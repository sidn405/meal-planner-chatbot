/* eslint-disable  func-names */
/* eslint-disable  no-console */

const Alexa = require('ask-sdk-core');
const axios = require('axios');

const BASE_URL = process.env.RAILWAY_BASE_URL || 'https://meal-planner-chatbot-production.up.railway.app';

function buildAbsoluteUrl(maybeRelative) {
  if (!maybeRelative) return null;
  if (maybeRelative.startsWith('http')) return maybeRelative;
  return `${BASE_URL}${maybeRelative}`;
}

// Very lightweight “make it speakable”
function toSpeakable(text) {
  if (!text) return '';
  return text
    .replace(/\*\*/g, '')            // remove markdown bold
    .replace(/[#>`_]/g, '')          // remove some markdown chars
    .replace(/\n+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

async function callRailwayChat(message) {
  // Your app expects JSON: { message: "..." } :contentReference[oaicite:2]{index=2}
  const url = `${BASE_URL}/chat`;
  const res = await axios.post(url, { message }, { timeout: 30000 });
  return res.data; // { response, content, pdf_url } :contentReference[oaicite:3]{index=3}
}

/**
 * Build a single message string that your Python backend already understands.
 * It extracts type/diet/cuisine/days/servings from the message text :contentReference[oaicite:4]{index=4}
 */
function buildMessageForIntent(intentName, slots) {
  const s = (name) => (slots && slots[name] && slots[name].value ? slots[name].value : null);

  const recipeQuery = s('RECIPE_QUERY');
  const ingredients = s('INGREDIENTS');
  const diet = s('DIET');
  const cuisine = s('CUISINE');
  const servings = s('SERVINGS');
  const days = s('DAYS');
  const store = s('STORE');

  // Compose “natural language” triggers (recipe / meal plan / grocery list)
  // so your extract_parameters() routes correctly. :contentReference[oaicite:5]{index=5}
  switch (intentName) {
    case 'GetRecipeIntent': {
      let msg = `Recipe for ${recipeQuery || 'something healthy'}.`;
      if (diet) msg += ` Dietary: ${diet}.`;
      if (cuisine) msg += ` Cuisine: ${cuisine}.`;
      if (servings) msg += ` Servings: ${servings}.`;
      return msg;
    }

    case 'PantryRecipeIntent': {
      let msg = `Recipe with ${ingredients || 'what I have on hand'}.`;
      if (diet) msg += ` Dietary: ${diet}.`;
      if (cuisine) msg += ` Cuisine: ${cuisine}.`;
      if (servings) msg += ` Servings: ${servings}.`;
      return msg;
    }

    case 'MealPlanIntent': {
      const d = days || 7;
      let msg = `Create a ${d}-day meal plan.`;
      if (diet) msg += ` Dietary: ${diet}.`;
      if (cuisine) msg += ` Cuisine: ${cuisine}.`;
      if (servings) msg += ` Servings: ${servings}.`;
      return msg;
    }

    case 'GroceryListIntent': {
      let msg = 'Generate grocery list.';
      if (diet) msg += ` Dietary: ${diet}.`;
      if (servings) msg += ` Servings: ${servings}.`;
      if (store) msg += ` Store: ${store}.`;
      return msg;
    }

    default:
      return 'Help me with a recipe, a meal plan, or a grocery list.';
  }
}

function saveLastDoc(handlerInput, docType, pdfFullUrl) {
  const attrs = handlerInput.attributesManager.getSessionAttributes();
  attrs.lastDocType = docType;
  attrs.lastPdfUrl = pdfFullUrl;
  handlerInput.attributesManager.setSessionAttributes(attrs);
}

function addCard(handlerInput, title, pdfFullUrl, extraText = '') {
  // Cards show in Alexa app / screen devices; URLs are typically tappable there.
  const cardText = `${extraText}\n\nPDF: ${pdfFullUrl}`;
  handlerInput.responseBuilder.withStandardCard(title, cardText);
}

async function handleGenerate(handlerInput, docTypeLabel) {
  const intent = handlerInput.requestEnvelope.request.intent;
  const intentName = intent.name;
  const slots = intent.slots;

  const message = buildMessageForIntent(intentName, slots);

  const data = await callRailwayChat(message);
  const responseText = data?.response || "Done.";
  const content = toSpeakable(data?.content || '');
  const pdfFullUrl = buildAbsoluteUrl(data?.pdf_url);

  // Keep speech short (voice UX)
  let speech = `${toSpeakable(responseText)} `;
  if (content) {
    // Speak just a snippet; your backend content is long.
    const snippet = content.length > 180 ? `${content.slice(0, 180)}...` : content;
    speech += snippet + ' ';
  }

  if (pdfFullUrl) {
    saveLastDoc(handlerInput, docTypeLabel, pdfFullUrl);
    speech += `I also sent the ${docTypeLabel} PDF link to your Alexa app.`;
    addCard(handlerInput, 'Healthy Eating Guru', pdfFullUrl, `Your ${docTypeLabel} is ready.`);
  } else {
    speech += `If you want, I can generate a PDF version too.`;
  }

  return handlerInput.responseBuilder
    .speak(speech)
    .reprompt('You can ask for another recipe, a meal plan, or a grocery list.')
    .getResponse();
}

const LaunchRequestHandler = {
  canHandle(handlerInput) {
    return Alexa.getRequestType(handlerInput.requestEnvelope) === 'LaunchRequest';
  },
  handle(handlerInput) {
    const speech = `Welcome to Healthy Eating Guru. You can say: recipe for chicken and vegetables, create a 7 day vegan meal plan, or generate a grocery list. What would you like?`;
    return handlerInput.responseBuilder
      .speak(speech)
      .reprompt('Try: recipe with chicken and broccoli.')
      .getResponse();
  },
};

const GetRecipeIntentHandler = {
  canHandle(handlerInput) {
    return Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest'
      && Alexa.getIntentName(handlerInput.requestEnvelope) === 'GetRecipeIntent';
  },
  async handle(handlerInput) {
    return handleGenerate(handlerInput, 'recipe');
  },
};

const PantryRecipeIntentHandler = {
  canHandle(handlerInput) {
    return Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest'
      && Alexa.getIntentName(handlerInput.requestEnvelope) === 'PantryRecipeIntent';
  },
  async handle(handlerInput) {
    return handleGenerate(handlerInput, 'recipe');
  },
};

const MealPlanIntentHandler = {
  canHandle(handlerInput) {
    return Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest'
      && Alexa.getIntentName(handlerInput.requestEnvelope) === 'MealPlanIntent';
  },
  async handle(handlerInput) {
    return handleGenerate(handlerInput, 'meal plan');
  },
};

const GroceryListIntentHandler = {
  canHandle(handlerInput) {
    return Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest'
      && Alexa.getIntentName(handlerInput.requestEnvelope) === 'GroceryListIntent';
  },
  async handle(handlerInput) {
    return handleGenerate(handlerInput, 'grocery list');
  },
};

const SendPdfIntentHandler = {
  canHandle(handlerInput) {
    return Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest'
      && Alexa.getIntentName(handlerInput.requestEnvelope) === 'SendPdfIntent';
  },
  handle(handlerInput) {
    const attrs = handlerInput.attributesManager.getSessionAttributes();
    const lastPdfUrl = attrs.lastPdfUrl;
    const lastDocType = attrs.lastDocType || 'document';

    if (!lastPdfUrl) {
      return handlerInput.responseBuilder
        .speak(`I don’t have a recent PDF yet. Ask me for a recipe, meal plan, or grocery list first.`)
        .reprompt('Try: create a 7 day meal plan.')
        .getResponse();
    }

    addCard(handlerInput, 'Healthy Eating Guru', lastPdfUrl, `Here’s your ${lastDocType} PDF link again.`);
    return handlerInput.responseBuilder
      .speak(`Sure. I sent the ${lastDocType} PDF link to your Alexa app.`)
      .reprompt('Want another recipe or a meal plan?')
      .getResponse();
  },
};

const HelpIntentHandler = {
  canHandle(handlerInput) {
    return Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest'
      && Alexa.getIntentName(handlerInput.requestEnvelope) === 'AMAZON.HelpIntent';
  },
  handle(handlerInput) {
    const speech = `You can say: recipe for salmon, or I have chicken and broccoli what can I make, or create a 7 day keto meal plan, or generate a grocery list.`;
    return handlerInput.responseBuilder.speak(speech).reprompt(speech).getResponse();
  },
};

const CancelAndStopIntentHandler = {
  canHandle(handlerInput) {
    return Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest'
      && (Alexa.getIntentName(handlerInput.requestEnvelope) === 'AMAZON.CancelIntent'
        || Alexa.getIntentName(handlerInput.requestEnvelope) === 'AMAZON.StopIntent');
  },
  handle(handlerInput) {
    return handlerInput.responseBuilder.speak('Goodbye!').getResponse();
  },
};

const FallbackIntentHandler = {
  canHandle(handlerInput) {
    return Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest'
      && Alexa.getIntentName(handlerInput.requestEnvelope) === 'AMAZON.FallbackIntent';
  },
  handle(handlerInput) {
    return handlerInput.responseBuilder
      .speak('Sorry, I didn’t catch that. Try asking for a recipe, a meal plan, or a grocery list.')
      .reprompt('Try: recipe with chicken and vegetables.')
      .getResponse();
  },
};

const ErrorHandler = {
  canHandle() {
    return true;
  },
  handle(handlerInput, error) {
    console.error('Error handled:', error);
    return handlerInput.responseBuilder
      .speak('Sorry, something went wrong calling the meal planner. Please try again.')
      .reprompt('Try: recipe for chicken.')
      .getResponse();
  },
};

exports.handler = Alexa.SkillBuilders.custom()
  .addRequestHandlers(
    LaunchRequestHandler,
    GetRecipeIntentHandler,
    PantryRecipeIntentHandler,
    MealPlanIntentHandler,
    GroceryListIntentHandler,
    SendPdfIntentHandler,
    HelpIntentHandler,
    CancelAndStopIntentHandler,
    FallbackIntentHandler
  )
  .addErrorHandlers(ErrorHandler)
  .lambda();
