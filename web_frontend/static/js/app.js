const API_URL = 'http://127.0.0.1:8000';
let user = null;
try {
    const storedUser = localStorage.getItem('user');
    if (storedUser && storedUser !== 'undefined') user = JSON.parse(storedUser);
} catch (e) {
    console.error("Clearing corrupted user data:", e);
    localStorage.clear();
}

document.addEventListener('DOMContentLoaded', () => {
    const path = window.location.pathname.split('/').pop() || 'index.html';

    // This router now correctly handles the separate welcome, login, customer, and admin pages.
    if (path === 'customer.html') {
        if (!localStorage.getItem('token')) return window.location.href = 'login.html';
        initCustomerPage();
    } else if (path === 'admin.html') {
        if (!localStorage.getItem('token') || !user?.is_admin) return window.location.href = 'login.html';
        initAdminPage();
    } else if (path === 'login.html') {
        // This is the key change: it correctly initializes the login page.
        initAuthPage();
    }
    // No special action is needed for the welcome page (index.html).
});

// --- AUTH PAGE (for login.html) LOGIC ---
function initAuthPage() {
    const sel = (id) => document.getElementById(id);
    const loginView = sel('login-view');
    const registerView = sel('register-view');

    // This logic correctly finds the elements on login.html and makes the buttons work.
    if (loginView && registerView) {
        sel('show-register').addEventListener('click', () => {
            loginView.style.display = 'none';
            registerView.style.display = 'block';
        });
        sel('show-login').addEventListener('click', () => {
            registerView.style.display = 'none';
            loginView.style.display = 'block';
        });
        sel('login-btn').addEventListener('click', handleLogin);
        sel('register-btn').addEventListener('click', handleRegister);
    }
}

async function handleLogin() {
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    const errorEl = document.getElementById('auth-error');
    const formData = new FormData();
    formData.append('username', email);
    formData.append('password', password);
    try {
        const data = await apiCall('/api/users/token', 'POST', formData, true);
        localStorage.setItem('token', data.access_token);
        localStorage.setItem('user', JSON.stringify(data.user));
        window.location.href = data.user.is_admin ? 'admin.html' : 'customer.html';
    } catch (error) {
        errorEl.textContent = error.message;
    }
}

async function handleRegister() {
    const email = document.getElementById('register-email').value;
    const password = document.getElementById('register-password').value;
    const errorEl = document.getElementById('auth-error');
    try {
        await apiCall('/api/users/register', 'POST', { email, password });
        alert('Registration successful! Please log in.');
        document.getElementById('show-login').click();
    } catch (error) {
        errorEl.textContent = error.message;
    }
}


// --- CUSTOMER PAGE (CUSTOMER.HTML) LOGIC ---
let applicationData = {};
let conversationState = 'ASK_NAME';

const conversationFlow = {
    'ASK_NAME': {
        validation: (message) => {
            if (message.split(' ').length < 2) return { success: false, error: "Please enter your full name (first and last name)." };
            return { success: true, value: message };
        },
        success: (value) => {
            applicationData.full_name = value;
            conversationState = 'ASK_GENDER';
            addBotMessage(`Thank you, ${value}. What is your gender? (Male / Female / Other)`);
        }
    },
    'ASK_GENDER': {
        validation: (message) => {
            const gender = message.toLowerCase();
            if (!['male', 'female', 'other'].includes(gender)) return { success: false, error: "Please enter a valid gender: Male, Female, or Other." };
            return { success: true, value: message };
        },
        success: (value) => {
            applicationData.gender = value;
            conversationState = 'ASK_MARRIED';
            addBotMessage("Are you married? (Yes / No)");
        }
    },
    'ASK_MARRIED': {
        validation: (message) => {
            const answer = message.toLowerCase();
            if (answer.includes('yes')) return { success: true, value: 'Yes' };
            if (answer.includes('no')) return { success: true, value: 'No' };
            return { success: false, error: "Please answer with 'Yes' or 'No'. Are you married?" };
        },
        success: (value) => {
            applicationData.married = value;
            conversationState = 'ASK_DEPENDENTS';
            addBotMessage("How many dependents do you have? (0, 1, 2, or 3+)");
        }
    },
    'ASK_DEPENDENTS': {
        validation: (message) => {
            if (!['0', '1', '2', '3+'].includes(message)) return { success: false, error: "Please choose from the options: 0, 1, 2, or 3+." };
            return { success: true, value: message };
        },
        success: (value) => {
            applicationData.dependents = value;
            conversationState = 'ASK_EDUCATION';
            addBotMessage("What is your education level? (Graduate / Not Graduate)");
        }
    },
    'ASK_EDUCATION': {
        validation: (message) => {
            const answer = message.toLowerCase();
            if (answer.includes('graduate')) return { success: true, value: 'Graduate' };
            if (answer.includes('not')) return { success: true, value: 'Not Graduate' };
            return { success: false, error: "Please answer with 'Graduate' or 'Not Graduate'." };
        },
        success: (value) => {
            applicationData.education = value;
            conversationState = 'ASK_SELF_EMPLOYED';
            addBotMessage("Are you self-employed? (Yes / No)");
        }
    },
    'ASK_SELF_EMPLOYED': {
        validation: (message) => {
            const answer = message.toLowerCase();
            if (answer.includes('yes')) return { success: true, value: 'Yes' };
            if (answer.includes('no')) return { success: true, value: 'No' };
            return { success: false, error: "Please answer with 'Yes' or 'No'. Are you self-employed?" };
        },
        success: (value) => {
            applicationData.self_employed = value;
            conversationState = 'ASK_INCOME';
            addBotMessage("What is your monthly income (e.g., 50000)?");
        }
    },
    'ASK_INCOME': {
        validation: (message) => {
            const cleanedMessage = message.replace(/,/g, '');
            if (!/^\d*\.?\d+$/.test(cleanedMessage)) return { success: false, error: "Please enter a valid number without any text or symbols." };
            const income = parseFloat(cleanedMessage);
            if (isNaN(income) || income <= 0) return { success: false, error: "Please enter a valid positive number for your income." };
            return { success: true, value: income };
        },
        success: (value) => {
            applicationData.monthly_income = value;
            conversationState = 'ASK_COAPPLICANT_INCOME';
            addBotMessage("What is your co-applicant's monthly income? (Enter 0 if none)");
        }
    },
    'ASK_COAPPLICANT_INCOME': {
        validation: (message) => {
            const cleanedMessage = message.replace(/,/g, '');
            if (!/^\d*\.?\d+$/.test(cleanedMessage)) return { success: false, error: "Please enter a valid number without any text or symbols." };
            const coIncome = parseFloat(cleanedMessage);
            if (isNaN(coIncome) || coIncome < 0) return { success: false, error: "Please enter a valid number (0 or more)." };
            return { success: true, value: coIncome };
        },
        success: (value) => {
            applicationData.coapplicant_income = value;
            conversationState = 'ASK_LOAN_AMOUNT';
            addBotMessage("How much loan are you requesting (in thousands, e.g., 150 for 1,50,000)?");
        }
    },
    'ASK_LOAN_AMOUNT': {
        validation: (message) => {
            const cleanedMessage = message.replace(/,/g, '');
            if (!/^\d*\.?\d+$/.test(cleanedMessage)) return { success: false, error: "Please enter a valid number without any text or symbols." };
            const amount = parseFloat(cleanedMessage);
            if (isNaN(amount) || amount <= 0) return { success: false, error: "Please enter a valid positive number for the loan amount." };
            return { success: true, value: amount };
        },
        success: (value) => {
            applicationData.loan_amount = value;
            conversationState = 'ASK_LOAN_TERM';
            addBotMessage("What is the loan term in months? (e.g., 360 for 30 years)");
        }
    },
    'ASK_LOAN_TERM': {
        validation: (message) => {
            if (!/^\d+$/.test(message)) return { success: false, error: "Please enter a whole number without any text or symbols." };
            const term = parseInt(message, 10);
            if (isNaN(term) || term <= 0) return { success: false, error: "Please enter a valid positive number of months." };
            return { success: true, value: term };
        },
        success: (value) => {
            applicationData.loan_amount_term = value;
            conversationState = 'ASK_CREDIT_HISTORY';
            addBotMessage("Have you met all your previous credit guidelines? (Yes / No)");
        }
    },
    'ASK_CREDIT_HISTORY': {
        validation: (message) => {
            const answer = message.toLowerCase();
            if (answer.includes('yes')) return { success: true, value: 1 };
            if (answer.includes('no')) return { success: true, value: 0 };
            return { success: false, error: "This is a critical question. Please answer 'Yes' or 'No'." };
        },
        success: (value) => {
            applicationData.credit_history = value;
            conversationState = 'ASK_PROPERTY_AREA';
            addBotMessage("In what type of area is the property located? (Urban / Semiurban / Rural)");
        }
    },
    'ASK_PROPERTY_AREA': {
        validation: (message) => {
            const area = message.toLowerCase();
            if (!['urban', 'semiurban', 'rural'].includes(area)) return { success: false, error: "Please choose from the options: Urban, Semiurban, or Rural." };
            return { success: true, value: message };
        },
        success: (value) => {
            applicationData.property_area = value;
            conversationState = 'CONFIRM_SUBMIT';
            addBotMessage("Thank you. I have all the details. Shall I submit your application now? (Yes / No)");
        }
    },
    'CONFIRM_SUBMIT': {
        validation: (message) => ({ success: true, value: message.toLowerCase() }),
        success: (value) => {
            if (value.includes('yes')) {
                conversationState = 'AWAITING_STATEMENT';
                addBotMessage("Great. As the final step, please upload your bank statement PDF and click Submit.");
                document.getElementById('chat-input-container').style.display = 'none';
                document.getElementById('bank-statement-upload-container').classList.remove('hidden');
            } else {
                conversationState = 'ASK_NAME';
                addBotMessage("Okay, let's start over. What is your full name?");
            }
        }
    }
};

function initCustomerPage() {
    document.getElementById('user-email').textContent = user.email;
    document.getElementById('logout-btn').addEventListener('click', handleLogout);
    document.getElementById('send-btn').addEventListener('click', handleUserInput);
    document.getElementById('chat-input').addEventListener('keypress', (e) => { if (e.key === 'Enter') handleUserInput(); });
    document.getElementById('mic-btn').addEventListener('click', handleVoiceInput);
    document.getElementById('upload-form').addEventListener('submit', handleUploadSubmit);
    document.getElementById('final-submit-btn').addEventListener('click', handleFinalSubmit);
    
    document.querySelectorAll('input[type="file"]').forEach(input => {
        input.onchange = () => {
            const fileName = input.files[0] ? input.files[0].name : "No file chosen";
            const labelSpan = document.getElementById(input.id + '-filename');
            if(labelSpan) labelSpan.textContent = fileName;
        };
    });
    
    loadUserApplications();
    startConversation();
}

function startConversation() {
    addBotMessage("Hello! Let's start your credit application. To begin, what is your full name?");
}

function handleUserInput() {
    const inputField = document.getElementById('chat-input');
    const message = inputField.value.trim();
    if (!message) return;
    addUserMessage(message);
    processMessage(message);
    inputField.value = '';
}

function processMessage(message) {
    const currentStateHandler = conversationFlow[conversationState];
    if (!currentStateHandler) return;

    const validationResult = currentStateHandler.validation(message);
    if (!validationResult.success) {
        addBotMessage(validationResult.error);
        return; 
    }
    
    if (currentStateHandler.success) {
        currentStateHandler.success(validationResult.value);
    }
}

async function handleFinalSubmit() {
    const fileInput = document.getElementById('bank-statement-file');
    if (fileInput.files.length === 0) {
        return addBotMessage("Please select your bank statement PDF to continue.");
    }
    addBotMessage("Submitting application and analyzing bank statement, please wait...");
    conversationState = 'SUBMITTING';
    const formData = new FormData();
    formData.append('app_data', JSON.stringify(applicationData));
    formData.append('bank_statement', fileInput.files[0]);
    try {
        const result = await apiCall('/api/applications', 'POST', formData, true);
        addBotMessage(`Application submitted (ID #${result.id}). Initial AI assessment: **${result.preliminary_decision}**. Please upload your other documents for final verification.`);
        document.getElementById('chatbot-container').style.display = 'none';
        const uploadSection = document.getElementById('upload-section');
        uploadSection.classList.remove('hidden');
        document.getElementById('app-id-display').textContent = result.id;
        uploadSection.dataset.appId = result.id;
    } catch (error) {
        addBotMessage("Sorry, an error occurred during submission: " + error.message);
    }
}

async function handleUploadSubmit(event) {
    event.preventDefault();
    const form = event.target;
    const appId = form.closest('#upload-section').dataset.appId;
    const formData = new FormData();

    const aadhaarInput = form.querySelector('#aadhaar-file');
    const salaryInput = form.querySelector('#salary-slip-file');

    if (!aadhaarInput || !salaryInput || aadhaarInput.files.length === 0 || salaryInput.files.length === 0) {
        alert('Please select both Aadhaar and Salary Slip files.');
        return;
    }

    formData.append('aadhaar_file', aadhaarInput.files[0]);
    formData.append('salary_slip_file', salaryInput.files[0]);

    try {
        await apiCall(`/api/applications/${appId}/documents`, 'POST', formData, true);
        alert('Documents uploaded! Verification is in progress.');
        window.location.reload();
    } catch (error) {
        alert('Upload failed: ' + error.message);
    }
}

async function loadUserApplications() {
    try {
        const apps = await apiCall('/api/applications/me');
        const tableBody = document.querySelector('#applications-table tbody');
        tableBody.innerHTML = apps.map(app => {
            const finalDecision = app.final_decision || 'Pending Review';
            const status = app.status.replace(/_/g, ' ');
            const reportUrl = `${API_URL}/reports/report_app_${app.id}.pdf`;
            return `
                <tr>
                    <td>${app.id}</td>
                    <td>${status}</td>
                    <td>${finalDecision}</td>
                    <td>${(app.status === 'approved' || app.status === 'rejected') ? `<a href="${reportUrl}" target="_blank">Download</a>` : 'N/A'}</td>
                </tr>
            `;
        }).join('');
    } catch (error) {
        console.error("Failed to load user applications:", error);
    }
}

// --- ADMIN PAGE ---
function initAdminPage() {
    document.getElementById('logout-btn').addEventListener('click', handleLogout);
    loadAdminApplications();
}

async function loadAdminApplications() {
    try {
        const apps = await apiCall('/api/admin/applications');
        const tableBody = document.querySelector('#admin-applications-table tbody');
        tableBody.innerHTML = apps.map(app => {
            const nameMatch = app.ocr_name_match === true ? '✅' : (app.ocr_name_match === false ? '❌' : 'N/A');
            const incomeMatch = app.ocr_income_match === true ? '✅' : (app.ocr_income_match === false ? '❌' : 'N/A');
            const actionButtons = app.status === 'pending_approval' ? `
                <button class="action-btn approve" data-id="${app.id}">Approve</button>
                <button class="action-btn reject" data-id="${app.id}">Reject</button>
            ` : (app.final_decision || 'Done');
            return `
                <tr>
                    <td>${app.id}</td>
                    <td>${app.owner.email}</td>
                    <td>
                        Prelim: ${app.preliminary_decision || 'N/A'}<br>
                        Verified: ${app.verified_decision || 'N/A'}
                    </td>
                    <td>Name Match: ${nameMatch}<br>Income Match: ${incomeMatch}</td>
                    <td>
                        ${app.aadhaar_path ? `<a href="${API_URL}/${app.aadhaar_path.replace(/\\/g, '/')}" target="_blank">Aadhaar</a>` : ''} | 
                        ${app.salary_slip_path ? `<a href="${API_URL}/${app.salary_slip_path.replace(/\\/g, '/')}" target="_blank">Salary</a>` : ''}
                    </td>
                    <td>${actionButtons}</td>
                </tr>
            `;
        }).join('');
        document.querySelectorAll('.action-btn').forEach(btn => btn.addEventListener('click', handleAdminAction));
    } catch(error) {
        console.error("Failed to load admin applications:", error);
    }
}

async function handleAdminAction(event) {
    const id = event.target.dataset.id;
    const action = event.target.classList.contains('approve') ? 'approve' : 'reject';
    try {
        await apiCall(`/api/admin/applications/${id}/${action}`, 'POST');
        alert(`Application #${id} has been ${action}d.`);
        loadAdminApplications();
    } catch (error) {
        alert(`Action failed: ${error.message}`);
    }
}

// --- HELPERS ---
function handleLogout() {
    localStorage.clear();
    window.location.href = 'index.html';
}

async function apiCall(endpoint, method = 'GET', body = null, isFormData = false) {
    const token = localStorage.getItem('token');
    const headers = {};
    const options = { method, headers };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    if (body) {
        if (isFormData) {
            options.body = body;
        } else {
            headers['Content-Type'] = 'application/json';
            options.body = JSON.stringify(body);
        }
    }
    const response = await fetch(API_URL + endpoint, options);
    if (!response.ok) {
        const errData = await response.json().catch(() => ({ detail: 'An unknown server error occurred.' }));
        throw new Error(errData.detail);
    }
    const contentType = response.headers.get("content-type");
    if (contentType && contentType.indexOf("application/json") !== -1) {
        return response.json();
    }
    return {};
}

// --- UI & VOICE ---
function addBotMessage(message) {
    const chatWindow = document.getElementById('chat-window');
    const typingIndicator = document.querySelector('.typing-indicator-container');
    if(chatWindow && typingIndicator) {
        typingIndicator.style.display = 'flex';
        setTimeout(() => {
            typingIndicator.style.display = 'none';
            chatWindow.innerHTML += `<div class="chat-message bot"><p>${message}</p></div>`;
            chatWindow.scrollTop = chatWindow.scrollHeight;
            speakText(message);
        }, 800);
    }
}

function addUserMessage(message) {
    const chatWindow = document.getElementById('chat-window');
    if(chatWindow) {
        chatWindow.innerHTML += `<div class="chat-message user"><p>${message}</p></div>`;
        chatWindow.scrollTop = chatWindow.scrollHeight;
    }
}

function handleVoiceInput() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return alert("Your browser does not support voice recognition.");
    const recognition = new SpeechRecognition();
    recognition.lang = navigator.language || 'en-US';
    const micBtn = document.getElementById('mic-btn');
    micBtn.classList.add('active');
    recognition.onresult = (event) => {
        document.getElementById('chat-input').value = event.results[0][0].transcript;
        handleUserInput();
    };
    recognition.onend = () => micBtn.classList.remove('active');
    recognition.start();
}

function speakText(text) {
    if ('speechSynthesis' in window) {
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = navigator.language || 'en-US';
        window.speechSynthesis.speak(utterance);
    }
}

