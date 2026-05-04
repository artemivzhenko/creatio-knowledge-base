using Terrasoft.Core;
using Terrasoft.Core.Factories;

/// <summary>
/// Demonstrates the ClassFactory + DefaultBinding pattern for dependency injection in Creatio.
/// Use this pattern to decouple components from concrete implementations:
/// define an interface, mark the default class with [DefaultBinding], and resolve via ClassFactory.
/// Custom packages can override the binding with their own implementation without touching base code.
/// This is the standard Creatio extension mechanism — used throughout the platform and Marketplace apps.
/// </summary>

// 1. Define the interface — describes the contract all implementations must follow
interface INotificationSender {
    void Send(string message);
}

// 2. Default implementation — registered without a Name, used when resolving without a name
[DefaultBinding(typeof(INotificationSender))]
class EmailNotificationSender : INotificationSender {
    private readonly UserConnection _userConnection;

    public EmailNotificationSender(UserConnection userConnection) {
        _userConnection = userConnection;
    }

    public void Send(string message) {
        // default email sending logic
    }
}

// 3. Alternative implementation — registered with a Name for explicit resolution
[DefaultBinding(typeof(INotificationSender), Name = "Sms")]
class SmsNotificationSender : INotificationSender {
    private readonly UserConnection _userConnection;

    public SmsNotificationSender(UserConnection userConnection) {
        _userConnection = userConnection;
    }

    public void Send(string message) {
        // SMS sending logic — overrides the default in custom packages if re-registered without Name
    }
}

// 4. Consumer — resolves the implementation through ClassFactory, never depends on a concrete class
class NotificationService {
    private readonly INotificationSender _sender;

    public NotificationService(UserConnection userConnection) {
        // Resolve the default binding — returns EmailNotificationSender unless overridden
        _sender = ClassFactory.Get<INotificationSender>(
            new ConstructorArgument("userConnection", userConnection));

        // Resolve a named binding explicitly:
        // _sender = ClassFactory.Get<INotificationSender>("Sms",
        //     new ConstructorArgument("userConnection", userConnection));
    }

    public void Notify(string message) {
        _sender.Send(message);
    }
}
