using System;
using System.Collections.Generic;
using global::Common.Logging;
using Terrasoft.Core;
using Terrasoft.Core.Factories;
using Terrasoft.Mail.Sender;

/// <summary>
/// Demonstrates how to send an email from backend C# code using HtmlEmailMessageSender.
/// Use this approach in event listeners, script tasks, or integration services
/// when you need to send a transactional email programmatically.
/// EmailClientFactory is resolved via ClassFactory so the mail provider (SMTP, Exchange, etc.)
/// is determined by the Creatio mailbox configuration — no hardcoded credentials in code.
/// </summary>
class HowToSendEmailFromBackend {

    private readonly ILog _log = LogManager.GetLogger("HowToSendEmailFromBackend");

    public void SendEmail(UserConnection userConnection) {
        var message = new EmailMessage {
            From    = "noreply@mycompany.com",
            To      = new List<string> { "recipient@example.com" },
            Subject = "Hello from Creatio",
            Body    = "<p>This is an <b>HTML</b> email sent from backend logic.</p>",
            Priority = EmailPriority.Normal
        };

        SendEmailMessage(userConnection, message);
    }

    // Build a message with optional CC, BCC, and priority
    public void SendEmailWithOptions(UserConnection userConnection,
        string from, List<string> to, List<string> cc, string subject, string body) {

        var message = new EmailMessage {
            From     = from,
            To       = to,
            Cc       = cc,
            Subject  = subject,
            Body     = body,
            Priority = EmailPriority.High
        };

        SendEmailMessage(userConnection, message);
    }

    // Core send method — resolves the mail provider from Creatio mailbox config via ClassFactory
    private void SendEmailMessage(UserConnection userConnection, EmailMessage message) {
        try {
            var emailClientFactory = ClassFactory.Get<EmailClientFactory>(
                new ConstructorArgument("userConnection", userConnection));

            new HtmlEmailMessageSender(emailClientFactory, userConnection).Send(message);

            _log.InfoFormat("[SendEmailMessage] Sent. Subject={0}, To={1}",
                message.Subject, string.Join(",", message.To));
        }
        catch (Exception ex) {
            _log.ErrorFormat("[SendEmailMessage] Failed. Subject={0}, Error={1}",
                message.Subject, ex.Message);
            throw;
        }
    }
}
