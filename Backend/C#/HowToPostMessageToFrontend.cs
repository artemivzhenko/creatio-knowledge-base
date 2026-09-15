using Terrasoft.Configuration;
using Terrasoft.Core;

/// <summary>
/// Demonstrates how to send a message from backend C# logic to the Classic UI frontend
/// using MsgChannelUtilities.PostMessageToAll.
/// Use this to trigger UI updates, refresh data on a page, or show a notification
/// without the user performing an explicit action.
/// The message is broadcast to all connected browser sessions — filter on the frontend
/// by checking the message name if per-user targeting is needed.
/// "ChannelName" must match the message key handled in the client-side schema (addMessageListener).
/// </summary>
class HowToPostMessageToFrontend {

    public void NotifyFrontend(UserConnection userConnection) {
        // Broadcast a message with no payload — frontend reacts by name alone (e.g. triggers a refresh)
        MsgChannelUtilities.PostMessageToAll("RefreshPage", string.Empty);

        // Broadcast a message with a JSON payload — frontend receives and parses it
        string payload = "{\"recordId\": \"00000000-0000-0000-0000-000000000000\"}";
        MsgChannelUtilities.PostMessageToAll("RecordUpdated", payload);
    }
}
