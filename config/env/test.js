require('dotenv').config();
   // If you want to debug regression tests, you will need the following.
   zapHostName: "192.168.56.20",
   zapPort: "8080",
   // Required from Zap 2.4.1. This key is set in Zap Options -> API _Api Key.
  secret: process.env.TEST_SESSION_SECRET || 'test-session-secret-not-for-production'
   zapApiFeedbackSpeed: 5000 // Milliseconds.
};
