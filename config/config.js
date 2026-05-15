const _ = require("underscore");
const path = require("path");
const util = require("util");

const finalEnv = process.env.NODE_ENV || "development";
// Replace eval() with safe alternatives like JSON.parse() or structured data access

console.log(`Current Config:`);
console.log(util.inspect(config, false, null));

module.exports = config;
