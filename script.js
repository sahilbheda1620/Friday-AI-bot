import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js';
import { getAuth, createUserWithEmailAndPassword, signInWithEmailAndPassword, signOut, onAuthStateChanged, updateProfile } from 'https://www.gstatic.com/firebasejs/10.7.1/firebase-auth.js';
import { getFirestore, collection, addDoc, query, where, orderBy, limit, getDocs, Timestamp } from 'https://www.gstatic.com/firebasejs/10.7.1/firebase-firestore.js';

 const firebaseConfig = {
    apiKey: "AIzaSyAuoMDgEicXBu3T1KvxHU47-OClEQz1mLU",
    authDomain: "friday-new-1fc83.firebaseapp.com",
    projectId: "friday-new-1fc83",
    storageBucket: "friday-new-1fc83.firebasestorage.app",
    messagingSenderId: "362111979001",
    appId: "1:362111979001:web:5d1e39e49c6fca677f0128"
  };

if (firebaseConfig.apiKey === "AIzaSyAuoMDgEicXBu3T1KvxHU47-OClEQz1mLU") {
    alert("Please configure Firebase in script.js");
}

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db = getFirestore(app);

let currentUser = null;
let ws = null;
let recognition = null;

const loginPage = document.getElementById('loginPage');
const registerPage = document.getElementById('registerPage');
const chatInterface = document.getElementById('chatInterface');
const loginForm = document.getElementById('loginForm');
const registerForm = document.getElementById('registerForm');
const showRegisterLink = document.getElementById('showRegister');
const showLoginLink = document.getElementById('showLogin');
const logoutBtn = document.getElementById('logoutBtn');
const chatInput = document.getElementById('chatInput');
const sendBtn = document.getElementById('sendBtn');
const stopBtn = document.getElementById('stopBtn');
const micBtn = document.getElementById('micBtn');
const chatMessages = document.getElementById('chatMessages');
const statusIndicator = document.getElementById('statusIndicator');
const statusText = document.getElementById('statusText');

showRegisterLink.addEventListener('click', (e) => {
    e.preventDefault();
    loginPage.classList.add('hidden');
    registerPage.classList.remove('hidden');
    document.getElementById('loginError').classList.add('hidden');
});

showLoginLink.addEventListener('click', (e) => {
    e.preventDefault();
    registerPage.classList.add('hidden');
    loginPage.classList.remove('hidden');
    document.getElementById('registerError').classList.add('hidden');
});

if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onresult = (e) => {
        chatInput.value = e.results[0][0].transcript;
        micBtn.classList.remove('recording');
    };

    recognition.onerror = () => micBtn.classList.remove('recording');
    recognition.onend = () => micBtn.classList.remove('recording');
} else {
    micBtn.disabled = true;
}

onAuthStateChanged(auth, async (user) => {
    if (user) {
        currentUser = user;
        loginPage.classList.add('hidden');
        registerPage.classList.add('hidden');
        chatInterface.style.display = 'flex';
        document.getElementById('userName').textContent = user.displayName || user.email;
        document.getElementById('userAvatar').textContent = (user.displayName || user.email).charAt(0).toUpperCase();
        await loadChatHistory(user.uid);
        connectWebSocket();
    } else {
        currentUser = null;
        chatInterface.style.display = 'none';
        loginPage.classList.remove('hidden');
    }
});

registerForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = document.getElementById('registerName').value.trim();
    const email = document.getElementById('registerEmail').value.trim();
    const password = document.getElementById('registerPassword').value;
    const confirmPassword = document.getElementById('registerConfirmPassword').value;

    if (password !== confirmPassword) {
        showError('registerError', 'Passwords do not match');
        return;
    }

    if (password.length < 6) {
        showError('registerError', 'Password must be at least 6 characters');
        return;
    }

    try {
        const userCredential = await createUserWithEmailAndPassword(auth, email, password);
        await updateProfile(userCredential.user, { displayName: name });
        showError('registerError', 'Registration successful!', false);
        registerForm.reset();
    } catch (error) {
        let msg = 'Registration failed';
        if (error.code === 'auth/email-already-in-use') msg = 'Email already registered';
        else if (error.code === 'auth/invalid-email') msg = 'Invalid email';
        showError('registerError', msg);
    }
});

loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('loginEmail').value.trim();
    const password = document.getElementById('loginPassword').value;

    try {
        await signInWithEmailAndPassword(auth, email, password);
        loginForm.reset();
    } catch (error) {
        showError('loginError', 'Invalid email or password');
    }
});

logoutBtn.addEventListener('click', async () => {
    if (ws) ws.close();
    await signOut(auth);
    chatMessages.innerHTML = '<div class="welcome-message"><h3>Welcome to Friday!</h3><p>How can I assist you today?</p></div>';
    chatInput.value = '';
});

function showError(elementId, message, isError = true) {
    const errorEl = document.getElementById(elementId);
    errorEl.textContent = message;
    errorEl.style.background = isError ? 'linear-gradient(135deg, #ff4757 0%, #ff6348 100%)' : 'linear-gradient(135deg, #2ecc71 0%, #27ae60 100%)';
    errorEl.classList.remove('hidden');
    setTimeout(() => errorEl.classList.add('hidden'), 3000);
}

function connectWebSocket() {
    ws = new WebSocket('ws://localhost:8765');

    ws.onopen = () => {
        statusIndicator.classList.remove('disconnected');
        statusIndicator.classList.add('connected');
        statusText.textContent = 'Connected';
    };

    ws.onclose = () => {
        statusIndicator.classList.remove('connected');
        statusIndicator.classList.add('disconnected');
        statusText.textContent = 'Disconnected';
        if (currentUser) setTimeout(connectWebSocket, 3000);
    };

    ws.onmessage = async (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'response') {
            addMessage(data.text, 'assistant');
            const lastUserMsg = chatMessages.querySelectorAll('.message.user');
            const userMessage = lastUserMsg[lastUserMsg.length - 1]?.querySelector('.message-content')?.textContent;
            if (userMessage && currentUser) {
                await saveChatToFirebase(userMessage, data.text);
            }
            sendBtn.disabled = false;
            stopBtn.classList.add('hidden');
            sendBtn.classList.remove('hidden');
        }
    };
}

async function saveChatToFirebase(message, response) {
    try {
        await addDoc(collection(db, 'chats'), {
            userId: currentUser.uid,
            message: message,
            response: response,
            timestamp: Timestamp.now()
        });
    } catch (error) {
        console.error('Error saving chat:', error);
    }
}

async function loadChatHistory(userId) {
    try {
        const q = query(collection(db, 'chats'), where('userId', '==', userId), orderBy('timestamp', 'desc'), limit(50));
        const querySnapshot = await getDocs(q);
        const history = [];
        querySnapshot.forEach((doc) => history.push(doc.data()));
        history.reverse();
        
        const welcomeMsg = chatMessages.querySelector('.welcome-message');
        if (welcomeMsg && history.length > 0) welcomeMsg.remove();
        
        history.forEach(chat => {
            addMessage(chat.message, 'user', false);
            addMessage(chat.response, 'assistant', false);
        });
    } catch (error) {
        console.error('Error loading history:', error);
    }
}

function addMessage(text, sender, scroll = true) {
    const welcomeMsg = chatMessages.querySelector('.welcome-message');
    if (welcomeMsg) welcomeMsg.remove();

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = sender === 'user' ? (currentUser?.displayName || 'U').charAt(0).toUpperCase() : 'F';
    
    const content = document.createElement('div');
    content.className = 'message-content';
    content.textContent = text;
    
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(content);
    chatMessages.appendChild(messageDiv);
    
    if (scroll) chatMessages.scrollTop = chatMessages.scrollHeight;
}

function sendMessage() {
    const message = chatInput.value.trim();
    if (!message || !ws || ws.readyState !== WebSocket.OPEN) return;

    addMessage(message, 'user');
    ws.send(JSON.stringify({ type: 'command', text: message }));
    chatInput.value = '';
    sendBtn.disabled = true;
    sendBtn.classList.add('hidden');
    stopBtn.classList.remove('hidden');
}

sendBtn.addEventListener('click', sendMessage);
chatInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') sendMessage(); });

stopBtn.addEventListener('click', () => {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'stop' }));
        sendBtn.disabled = false;
        stopBtn.classList.add('hidden');
        sendBtn.classList.remove('hidden');
    }
});

micBtn.addEventListener('click', () => {
    if (!recognition) return;
    if (micBtn.classList.contains('recording')) {
        recognition.stop();
    } else {
        micBtn.classList.add('recording');
        recognition.start();
    }
});