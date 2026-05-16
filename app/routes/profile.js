const ProfileDAO = require("../data/profile-dao").ProfileDAO;
const ESAPI = require("node-esapi");
const {
    environmentalScripts
} = require("../../config/config");

/* The ProfileHandler must be constructed with a connected db */
function ProfileHandler(db) {
    "use strict";

    const profile = new ProfileDAO(db);

    this.displayProfile = (req, res, next) => {
        const {
            userId
        } = req.session;



        profile.getByUserId(parseInt(userId), (err, doc) => {
            if (err) return next(err);
            doc.userId = userId;

            // @TODO @FIXME
            // while the developer intentions were correct in encoding the user supplied input so it
            // doesn't end up as an XSS attack, the context is incorrect as it is encoding the firstname for HTML
            // while this same variable is also used in the context of a URL link element
            doc.website = ESAPI.encoder().encodeForHTML(doc.website);
            // fix it by replacing the above with another template variable that is used for 
            // the context of a URL in a link header
            // doc.website = ESAPI.encoder().encodeForURL(doc.website)

            return res.render("profile", {
                ...doc,
                environmentalScripts
            });
        });
    };

// Fixed code with output encoding
const escapeHtml = (str) => {
    return str.replace(/[&<>"']/g, (char) => {
        return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[char];
    });
};
res.send("<html><body>" + escapeHtml(userInput) + "</body></html>");

// Alternative: Use template engine with auto-escaping (e.g., Pug, Handlebars)
// Fixed code with output encoding
const escapeHtml = (str) => {
    return str.replace(/[&<>"']/g, (char) => {
        return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[char];
    });
};
res.send("<html><body>" + escapeHtml(userInput) + "</body></html>");

// Alternative: Use template engine with auto-escaping (e.g., Pug, Handlebars)
// Fixed code with output encoding
const escapeHtml = (str) => {
    return str.replace(/[&<>"']/g, (char) => {
        return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[char];
    });
};
res.send("<html><body>" + escapeHtml(userInput) + "</body></html>");

// Alternative: Use template engine with auto-escaping (e.g., Pug, Handlebars)
// Fixed code with output encoding
const escapeHtml = (str) => {
    return str.replace(/[&<>"']/g, (char) => {
        return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[char];
    });
};
res.send("<html><body>" + escapeHtml(userInput) + "</body></html>");

// Alternative: Use template engine with auto-escaping (e.g., Pug, Handlebars)
// Fixed code with output encoding
const escapeHtml = (str) => {
    return str.replace(/[&<>"']/g, (char) => {
        return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[char];
    });
};
res.send("<html><body>" + escapeHtml(userInput) + "</body></html>");

// Alternative: Use template engine with auto-escaping (e.g., Pug, Handlebars)
// Fixed code with output encoding
const escapeHtml = (str) => {
    return str.replace(/[&<>"']/g, (char) => {
        return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[char];
    });
};
res.send("<html><body>" + escapeHtml(userInput) + "</body></html>");

// Alternative: Use template engine with auto-escaping (e.g., Pug, Handlebars)
            const firstNameSafeString = firstName;
// Fixed code with output encoding
const escapeHtml = (str) => {
    return str.replace(/[&<>"']/g, (char) => {
        return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[char];
    });
};
res.send("<html><body>" + escapeHtml(userInput) + "</body></html>");

// Alternative: Use template engine with auto-escaping (e.g., Pug, Handlebars)
                ssn,
                dob,
                address,
                bankAcc,
                bankRouting,
// Fixed code with output encoding
const escapeHtml = (str) => {
    return str.replace(/[&<>"']/g, (char) => {
        return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[char];
    });
};
res.send("<html><body>" + escapeHtml(userInput) + "</body></html>");

// Alternative: Use template engine with auto-escaping (e.g., Pug, Handlebars)

        profile.updateUser(
            parseInt(userId),
            firstName,
// Fixed code with output encoding
const escapeHtml = (str) => {
    return str.replace(/[&<>"']/g, (char) => {
        return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[char];
    });
};
res.send("<html><body>" + escapeHtml(userInput) + "</body></html>");

// Alternative: Use template engine with auto-escaping (e.g., Pug, Handlebars)
            bankAcc,
            bankRouting,
            (err, user) => {

                if (err) return next(err);

                // WARN: Applying any sting specific methods here w/o checking type of inputs could lead to DoS by HPP
                //firstName = firstName.trim();
                user.updateSuccess = true;
                user.userId = userId;

                return res.render("profile", {
                    ...user,
                    environmentalScripts
                });
            }
        );

    };

}

module.exports = ProfileHandler;
