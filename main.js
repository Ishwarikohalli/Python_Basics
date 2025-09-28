
document.addEventListener("DOMContentLoaded", () => {
    // Detect which page is loaded
    const signupForm = document.getElementById("signup-form");
    const chatBox = document.getElementById("chat-box");

    // ✅ 1. SIGNUP PAGE FUNCTIONALITY
    if (signupForm) {
        signupForm.addEventListener("submit", async (e) => {
            e.preventDefault();

            const name = document.getElementById("name").value;
            const email = document.getElementById("email").value;
            const password = document.getElementById("password").value;

            const payload = {
                name: name,
                email: email,
                password: password
            };

            try {
                const response = await fetch("http://127.0.0.1:8000/api/signup", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify(payload)
                });

                if (response.ok) {
                    const data = await response.json();
                    alert(data.message);
                    window.location.href = "login.html";
                } else {
                    const error = await response.json();
                    alert("Signup failed: " + error.detail);
                }
            } catch (error) {
                alert("An error occurred: " + error.message);
                console.error("Error during signup:", error);
            }
        });
    }

    // ✅ 2. CHATBOT PAGE FUNCTIONALITY
    if (chatBox) {
        const userInput = document.getElementById('user-input');
        const sendBtn = document.getElementById('send-btn');
        const subjectSelect = document.getElementById('subject-select');

        // Generate or get student ID
        const studentId = localStorage.getItem('studentId') ||
            'student-' + Math.random().toString(36).substr(2, 9);
        localStorage.setItem('studentId', studentId);

        // Initial greeting
        addMessage('bot', "Hello! I'm your AI learning assistant. How can I help you today? 😊");

        // Send message
        async function sendMessage() {
            const message = userInput.value.trim();
            if (!message) return;

            addMessage('user', message);
            userInput.value = '';
            showTypingIndicator();

            try {
                const response = await fetch('http://localhost:8000/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        content: message,
                        subject: subjectSelect.value,
                        user_id: studentId
                    }),
                });

                if (!response.ok) {
                    throw new Error(await response.text());
                }

                const data = await response.json();
                removeTypingIndicator();
                addMessage('bot', formatBotResponse(data.response));
            } catch (error) {
                console.error('Error:', error);
                removeTypingIndicator();
                addMessage('bot', '🤖 **Oops!** I encountered an error. Please try again.');
            }
        }

        function formatBotResponse(response) {
            return `${response.replace(/\n/g, '\n• ')}`;
        }

        function addMessage(sender, text) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${sender}-message`;
            if (sender === 'bot') text = formatBotResponse(text);
            messageDiv.innerHTML = text;
            chatBox.appendChild(messageDiv);
            chatBox.scrollTop = chatBox.scrollHeight;
        }

        function showTypingIndicator() {
            const typingDiv = document.createElement('div');
            typingDiv.className = 'message bot-message typing-indicator';
            typingDiv.textContent = '🤖 Typing...';
            typingDiv.id = 'typing-indicator';
            chatBox.appendChild(typingDiv);
            chatBox.scrollTop = chatBox.scrollHeight;
        }

        function removeTypingIndicator() {
            const indicator = document.getElementById('typing-indicator');
            if (indicator) indicator.remove();
        }

        // Event listeners
        sendBtn.addEventListener('click', sendMessage);
        userInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
    }
});
let facts = [];
let currentIndex = 0;

const fetchHistoricalFacts = async () => {
    try {
        const response = await fetch("https://history.muffinlabs.com/date");
        const data = await response.json();
        facts = data.data.Events.map(event => `${event.year} — ${event.text}`);
        currentIndex = 0;
        updateFact();
    } catch (error) {
        console.error("Error fetching historical facts:", error);
        document.querySelector(".carousel-item").textContent = "Failed to load history.";
    }
};

const updateFact = () => {
    const carouselItem = document.querySelector(".carousel-item");
    if (facts.length > 0) {
        carouselItem.textContent = facts[currentIndex];
    } else {
        carouselItem.textContent = "No facts available today.";
    }
};

document.getElementById("refreshBtn").addEventListener("click", () => {
    currentIndex = (currentIndex + 1) % facts.length;
    updateFact();
});

window.addEventListener("DOMContentLoaded", fetchHistoricalFacts);
