using System;
using System.ServiceModel;
using System.ServiceModel.Activation;
using System.ServiceModel.Web;
using Terrasoft.Core;
using Terrasoft.Core.Factories;
using Terrasoft.Web.Common;
using Terrasoft.Web.Common.ServiceRouting;

/// <summary>
/// Demonstrates the service ROUTING attributes that decide which URLs a configuration
/// service is reachable on, and the ClassFactory + ConstructorArgument pattern that keeps
/// the service itself thin.
///
/// ROUTE ATTRIBUTES (Terrasoft.Web.Common.ServiceRouting):
///   [DefaultServiceRoute]  registers the service on the main application route,
///                          /0/rest/&lt;ServiceName&gt;/&lt;MethodName&gt; — for authenticated
///                          back-office users.
///   [SspServiceRoute]      additionally registers it on the portal (self-service) route,
///                          so portal users can call it.
/// Without either attribute the service is only reachable through the legacy
/// ServiceModel path. Declaring both is the usual choice for a service that serves the
/// main app and the portal alike.
///
/// [SspServiceRoute] MAKES THE SERVICE REACHABLE, IT DOES NOT AUTHORISE IT. Portal users
/// still need the operation permission, and the service still has to check what the caller
/// is allowed to see. Exposing a service to the portal without narrowing its queries is the
/// classic way to leak back-office data. See HowToExposeServiceToPortalUsers.
///
/// THIN SERVICE, FAT HELPER. Keep the service class to routing, argument shape and the
/// call into a helper resolved through ClassFactory:
///
///   ClassFactory.Get&lt;THelper&gt;(new ConstructorArgument("userConnection", UserConnection))
///
/// The name in ConstructorArgument must match the helper's constructor PARAMETER NAME
/// exactly - it is matched by name, not by position, and a mismatch throws at runtime, not
/// at compile time. Resolving through the factory is what lets another package override the
/// helper with [Override] without touching this service.
///
/// BaseService gives the service UserConnection for the authenticated caller. Use that
/// connection, not SystemUserConnection, unless the operation genuinely needs to bypass
/// permissions - see HowToUseSystemUserConnection.
/// </summary>
namespace Terrasoft.Configuration
{

	[DefaultServiceRoute]
	[SspServiceRoute]
	[ServiceContract]
	[AspNetCompatibilityRequirements(RequirementsMode = AspNetCompatibilityRequirementsMode.Required)]
	public class UsrConversationWebService : BaseService
	{

		/// <summary>
		/// POST /0/rest/UsrConversationWebService/CreateCallSummary
		/// Body: { "callId": "...", "leadId": "..." }
		/// </summary>
		[OperationContract]
		[WebInvoke(Method = "POST", BodyStyle = WebMessageBodyStyle.Wrapped,
			RequestFormat = WebMessageFormat.Json, ResponseFormat = WebMessageFormat.Json)]
		public void CreateCallSummary(Guid callId, Guid leadId) {
			var helper = ClassFactory.Get<UsrCallTranscriptionHelper>(
				new ConstructorArgument("userConnection", UserConnection));
			helper.SummarizeTranscription(callId, leadId);
		}

		/// <summary>
		/// Returning a value: the JSON response is wrapped, so the client reads it under
		/// "&lt;MethodName&gt;Result" - here "TransferAudioToTranscriptionResult".
		/// </summary>
		[OperationContract]
		[WebInvoke(Method = "POST", BodyStyle = WebMessageBodyStyle.Wrapped,
			RequestFormat = WebMessageFormat.Json, ResponseFormat = WebMessageFormat.Json)]
		public string TransferAudioToTranscription(Guid callId) {
			var helper = ClassFactory.Get<UsrCallTranscriptionHelper>(
				new ConstructorArgument("userConnection", UserConnection));
			return helper.TransferAudioToTranscription(callId);
		}

		/// <summary>
		/// A GET endpoint. UriTemplate names the query-string parameters.
		/// </summary>
		[OperationContract]
		[WebGet(UriTemplate = "GetCallStatus?callId={callId}",
			ResponseFormat = WebMessageFormat.Json)]
		public string GetCallStatus(Guid callId) {
			var helper = ClassFactory.Get<UsrCallTranscriptionHelper>(
				new ConstructorArgument("userConnection", UserConnection));
			return helper.GetStatus(callId);
		}
	}

	/// <summary>
	/// The helper holds the logic. The constructor parameter is named "userConnection",
	/// which is the name the service passes to ConstructorArgument.
	/// </summary>
	public class UsrCallTranscriptionHelper
	{
		protected UserConnection UserConnection { get; set; }

		public UsrCallTranscriptionHelper(UserConnection userConnection) {
			UserConnection = userConnection;
		}

		public virtual void SummarizeTranscription(Guid callId, Guid leadId) { }

		public virtual string TransferAudioToTranscription(Guid callId) {
			return "OK";
		}

		public virtual string GetStatus(Guid callId) {
			return "done";
		}
	}
}
