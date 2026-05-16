const AllocationsDAO = require("../data/allocations-dao").AllocationsDAO;
const {
    environmentalScripts
} = require("../../config/config");

function AllocationsHandler(db) {
    "use strict";

    const allocationsDAO = new AllocationsDAO(db);

    this.displayAllocations = (req, res, next) => {
        /*
        // Fix for A4 Insecure DOR -  take user id from session instead of from URL param
// Fixed code with output encoding
const escapeHtml = (str) => {
    return str.replace(/[&<>"']/g, (char) => {
        return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[char];
    });
};
res.send("<html><body>" + escapeHtml(userInput) + "</body></html>");

// Alternative: Use template engine with auto-escaping (e.g., Pug, Handlebars)
        } = req.params;
        const {
            threshold
        } = req.query;

        allocationsDAO.getByUserIdAndThreshold(userId, threshold, (err, allocations) => {
            if (err) return next(err);
            return res.render("allocations", {
                userId,
                allocations,
                environmentalScripts
            });
        });
    };
}

module.exports = AllocationsHandler;
// Fixed code with output encoding
const escapeHtml = (str) => {
    return str.replace(/[&<>"']/g, (char) => {
        return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[char];
    });
};
res.send("<html><body>" + escapeHtml(userInput) + "</body></html>");

// Alternative: Use template engine with auto-escaping (e.g., Pug, Handlebars)
