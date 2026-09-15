using System.IO;
using System.ServiceModel;
using System.ServiceModel.Activation;
using System.ServiceModel.Web;
using System.Web;
using Terrasoft.Web.Common;

/// <summary>
/// Pattern: receive a file uploaded by the client inside a custom web service.
///
/// File upload must use multipart/form-data — standard for browser file inputs.
/// Access the uploaded files through HttpContextAccessor rather than HttpContext.Current
/// so the service stays testable and compatible with Creatio's request pipeline.
///
/// Two common patterns:
///   1. Access by field name — when the form always sends a field called "file".
///   2. Iterate all uploaded files — when the client may send one or several files.
///
/// Namespace must follow the pattern Terrasoft.Configuration.{ServiceName}Namespace.
/// </summary>
namespace Terrasoft.Configuration.FileUploadServiceNamespace {

    [ServiceContract]
    [DefaultServiceRoute]
    [AspNetCompatibilityRequirements(RequirementsMode = AspNetCompatibilityRequirementsMode.Required)]
    public class FileUploadService : BaseService {

        [OperationContract]
        [WebInvoke(Method = "POST",
            RequestFormat  = WebMessageFormat.Json,
            BodyStyle      = WebMessageBodyStyle.Wrapped,
            ResponseFormat = WebMessageFormat.Json)]
        public string UploadFile() {
            HttpFileCollection files = HttpContextAccessor.GetInstance().Request.Files;

            if (files.Count == 0)
                return "no file received";

            // Pattern 1: access by form field name
            HttpPostedFile file     = files["file"];
            string         fileName = file.FileName;
            Stream         stream   = file.InputStream;
            // process stream...

            return string.Format("received: {0} ({1} bytes)", fileName, file.ContentLength);
        }

        [OperationContract]
        [WebInvoke(Method = "POST",
            RequestFormat  = WebMessageFormat.Json,
            BodyStyle      = WebMessageBodyStyle.Wrapped,
            ResponseFormat = WebMessageFormat.Json)]
        public int UploadMultipleFiles() {
            HttpFileCollection files = HttpContextAccessor.GetInstance().Request.Files;

            // Pattern 2: iterate all uploaded files
            foreach (string key in files.AllKeys) {
                HttpPostedFile file   = files[key];
                Stream         stream = file.InputStream;
                // process each file...
            }

            return files.Count;
        }
    }
}
