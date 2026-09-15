using System;
using Terrasoft.Core;
using Terrasoft.Messaging.Common;

/// <summary>
/// Demonstrates how to send a message to the current user's browser session
/// using MsgChannelManager.
/// Use this when you need to notify a specific user — not all connected clients —
/// for example after a long background operation completes or to trigger a page reload.
/// MsgChannelManager.Instance.FindItemByUId(userId) resolves the WebSocket channel
/// for the given user. If the user has no active session the channel is null — always null-check.
/// The "Sender" in the message header acts as the message type key; the frontend
/// listens for it with addMessageListener("SenderName", handler).
/// For broadcasting to ALL connected users use MsgChannelUtilities.PostMessageToAll()
/// — see HowToPostMessageToFrontend.
/// </summary>
class HowToPostMessageToCurrentUser {

    // 1. Send a message to the currently logged-in user with a body payload
    public void NotifyCurrentUser(UserConnection userConnection, string messageType, string body) {
        // Resolve the WebSocket channel for this specific user
        var channel = MsgChannelManager.Instance.FindItemByUId(userConnection.CurrentUser.Id);

        if (channel == null) {
            // User has no active browser session — message cannot be delivered
            return;
        }

        var message = new SimpleMessage {
            Body   = body,
            Header = { Sender = messageType }
        };

        channel.PostMessage(message);
    }

    // 2. Send a message tied to a specific record Id — frontend can use it for targeted reload
    public void NotifyCurrentUserWithRecord(UserConnection userConnection,
        string messageType, Guid recordId, string body) {

        var channel = MsgChannelManager.Instance.FindItemByUId(userConnection.CurrentUser.Id);
        if (channel == null) return;

        var message = new SimpleMessage {
            Body   = body,
            Id     = recordId,     // record the notification is about
            Header = { Sender = messageType }
        };

        channel.PostMessage(message);
    }

    // 3. Send a message to a specific user by their Id (not the current user)
    public void NotifyUserById(UserConnection userConnection,
        Guid targetUserId, string messageType, string body) {

        var channel = MsgChannelManager.Instance.FindItemByUId(targetUserId);
        if (channel == null) return;

        channel.PostMessage(new SimpleMessage {
            Body   = body,
            Header = { Sender = messageType }
        });
    }
}
