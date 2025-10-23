import React from 'react';
import Chatbot from 'react-chatbot-kit';
import 'react-chatbot-kit/build/main.css';

const config = {
    initialMessages: [
        {
            id: 1,
            message: "Hello! I'm here to help you with your credit application. What is your full name?",
            widget: undefined,
        },
    ],
    botName: 'CreditBot',
};

const ActionProvider = ({ createChatBotMessage, setState, children }) => {
    const handleHello = () => {
        const botMessage = createChatBotMessage('Hello. Nice to meet you.');
        setState((prev) => ({
            ...prev,
            messages: [...prev.messages, botMessage],
        }));
    };

    // Example action to handle the user's name and ask the next question
    const handleName = (userName) => {
        const botMessage = createChatBotMessage(`Thank you, ${userName}. What is your monthly income?`);
        setState((prev) => ({
            ...prev,
            messages: [...prev.messages, botMessage],
        }));
    };


    return (
        <div>
            {React.Children.map(children, (child) => {
                return React.cloneElement(child, {
                    actions: {
                        handleHello,
                        handleName,
                        // Add other actions for your conversation flow here
                    },
                });
            })}
        </div>
    );
};

const MessageParser = ({ children, actions }) => {
    const parse = (message) => {
        const lowerCaseMessage = message.toLowerCase();

        if (lowerCaseMessage.includes('hello')) {
            actions.handleHello();
        }

        // This is a simple logic to handle the conversation flow.
        // A real application would need more robust state management to know which question was last asked.
        if (children.props.state.messages.length <= 2) {
             actions.handleName(message);
        }
    };

    return (
        <div>
            {React.Children.map(children, (child) => {
                return React.cloneElement(child, {
                    parse: parse,
                    actions,
                });
            })}
        </div>
    );
};


const AppChatbot = () => {
    return (
        <div>
            <Chatbot
                config={config}
                messageParser={MessageParser}
                actionProvider={ActionProvider}
            />
        </div>
    );
};

export default AppChatbot;

