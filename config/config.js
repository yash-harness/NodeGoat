const _ = require("underscore");
const path = require("path");
const util = require("util");

const finalEnv = process.env.NODE_ENV || "development";

const allConf = require(path.resolve(__dirname + "/../config/env/all.js"));
const envConf = require(path.resolve(__dirname + "/../config/env/" + finalEnv.toLowerCase() + ".js")) || {};

const config = { ...allConf, ...envConf };
// TODO: Review and fix security vulnerability

// TODO: Review and fix security vulnerability
console.log(`Current Config:`);
console.log(util.inspect(config, false, null));

module.exports = config;
