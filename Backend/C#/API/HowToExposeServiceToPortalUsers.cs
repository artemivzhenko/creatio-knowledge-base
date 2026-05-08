using System.ServiceModel;
using System.ServiceModel.Activation;
using System.ServiceModel.Web;
using Terrasoft.Web.Common;

/// <summary>
/// Pattern: expose a custom web service to portal (SSP) users.
///
/// By default, custom services are only accessible to internal (non-portal) users.
/// Add [SspServiceRoute] alongside [DefaultServiceRoute] to enable portal-side access.
///
/// URL mapping:
///   Internal users  → /0/ServiceModel/MyPortalService.svc/...
///   Portal (SSP)    → /0/ssp/ServiceModel/MyPortalService.svc/...
///
/// Both routes point to the same service class; Creatio enforces authentication
/// separately for each URL prefix.
///
/// Namespace must follow the pattern Terrasoft.Configuration.{ServiceName}Namespace.
/// </summary>
namespace Terrasoft.Configuration.MyPortalServiceNamespace {

    [ServiceContract]
    [DefaultServiceRoute]
    [SspServiceRoute]
    [AspNetCompatibilityRequirements(RequirementsMode = AspNetCompatibilityRequirementsMode.Required)]
    public class MyPortalService : BaseService {

        [OperationContract]
        [WebInvoke(Method = "GET",
            RequestFormat  = WebMessageFormat.Json,
            BodyStyle      = WebMessageBodyStyle.Wrapped,
            ResponseFormat = WebMessageFormat.Json)]
        public string Ping() {
            return "ok";
        }
    }
}
