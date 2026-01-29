<?php
add_action('wp_footer', function() {
?>
<!-- Meal Planner Chat Widget -->
<style>
#meal-chat-button {
    position: fixed;
    bottom: 20px;
    right: 20px;
    width: 65px;
    height: 65px;
    border-radius: 50%;
    background: linear-gradient(135deg, #f8e915 0%, #fe980a 100%);
    border: 3px solid #27a130;
    box-shadow: 0 4px 20px rgba(39,161,48,0.4);
    cursor: pointer;
    z-index: 9998;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 30px;
    transition: all 0.3s ease;
}

#meal-chat-button:hover {
    transform: scale(1.15);
    box-shadow: 0 6px 30px rgba(39,161,48,0.6);
}

#meal-chat-container {
    position: fixed;
    bottom: 100px;
    right: 20px;
    width: 420px;
    height: 650px;
    border-radius: 20px;
    box-shadow: 0 10px 50px rgba(0,0,0,0.4);
    z-index: 9999;
    display: none;
    overflow: hidden;
    background: white;
    border: 3px solid #27a130;
}

#meal-chat-container.open {
    display: block;
    animation: slideUp 0.4s ease;
}

@keyframes slideUp {
    from { opacity: 0; transform: translateY(30px); }
    to { opacity: 1; transform: translateY(0); }
}

#meal-chat-header {
    background: linear-gradient(135deg, #f8e915 0%, #fe980a 100%);
    color: white;
    padding: 18px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

#meal-chat-close {
    background: rgba(255,255,255,0.2);
    border: none;
    color: white;
    font-size: 28px;
    cursor: pointer;
    width: 35px;
    height: 35px;
    border-radius: 50%;
    transition: all 0.3s ease;
}

#meal-chat-close:hover {
    background: #fe980a;
    transform: rotate(90deg);
}

#meal-chat-iframe {
    width: 100%;
    height: calc(100% - 75px);
    border: none;
}

@media (max-width: 768px) {
    #meal-chat-container {
        width: 100%;
        height: 100%;
        bottom: 0;
        right: 0;
        border-radius: 0;
    }
    #meal-chat-button {
        width: 60px;
        height: 60px;
        bottom: 15px;
        right: 15px;
    }
}
</style>

<button id="meal-chat-button" onclick="toggleMealChat()">🥗</button>

<div id="meal-chat-container">
    <div id="meal-chat-header">
        <div>
            <h3 style="margin:0;font-size:17px;">🥗 Healthy Eating Guru</h3>
            <p style="margin:0;font-size:12px;opacity:0.9;">AI-Powered Meal Planning</p>
        </div>
        <button id="meal-chat-close" onclick="toggleMealChat()">×</button>
    </div>
    <iframe 
        id="meal-chat-iframe"
        src="https://meal-planner-chatbot-production.up.railway.app"
        title="Meal Planner Chat">
    </iframe>
</div>

<script>
function toggleMealChat() {
    const container = document.getElementById('meal-chat-container');
    const button = document.getElementById('meal-chat-button');
    container.classList.toggle('open');
}
</script>
<?php
}, 999);