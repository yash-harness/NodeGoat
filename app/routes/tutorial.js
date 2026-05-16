const express = require("express");
const {
    environmentalScripts
} = require("../../config/config");

const router = express.Router();

router.get("/", (req, res) => {
    "use strict";
    return res.render("tutorial/a1", {
        environmentalScripts
    });
});

const pages = [
    "a1",
    "a2",
    "a3",
    "a4",
    "a5",
    "a6",
    "a7",
    "a8",
    "a9",
    "a10",
    "redos",
    "ssrf"
];

for(const page of pages) {
// Apply security best practices:
// 1. Validate and sanitize all user inputs
// 2. Use parameterized queries/prepared statements
// 3. Apply output encoding based on context
// 4. Implement least privilege principle
// 5. Add security headers and CSP
}

module.exports = router;
