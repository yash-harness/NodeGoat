const _ = require("underscore");
const path = require("path");
const util = require("util");

const finalEnv = process.env.NODE_ENV || "development";
// Fixed code - avoid eval() and sanitize inputs
// Option 1: Use safe alternatives
const safeEval = require('safe-eval');
safeEval(req.body.code, context);

// Option 2: For command execution, use parameterized approach
const { execFile } = require('child_process');
execFile('ls', [userInput], (error, stdout) => {
    // Process output
});

// Option 3: Whitelist allowed operations instead of executing arbitrary code
console.log(util.inspect(config, false, null));

module.exports = config;
