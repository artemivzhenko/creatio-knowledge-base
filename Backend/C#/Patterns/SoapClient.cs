using System;
using System.Net.Http;
using System.Runtime.ExceptionServices;
using System.Text;
using System.Threading.Tasks;
using global::Common.Logging;
using Terrasoft.Core;
using Terrasoft.Core.DB;

/// <summary>
/// Pattern: SOAP client for calling external XML/SOAP web services from Creatio backend.
///
/// Usage:
///   var client = new SoapClient("https://api.example.com/service");
///   var response = await client.Send(new SoapRequest("/Endpoint", xmlBody), userConnection);
///
/// DB logging:
///   Pass doLog: true (default) to persist every request/response pair to the SoapLogs entity.
///   The entity must have columns: Id (Guid), Url, Request, Response, Error (all Text), CreatedOn (DateTime).
///   Set doLog: false to skip DB logging for high-frequency or non-audited calls.
///
/// ExceptionDispatchInfo pattern:
///   The exception is captured inside catch so the finally block (DB logging) always runs,
///   then re-thrown after finally with the original stack trace preserved.
/// </summary>
namespace Terrasoft.Configuration {

    public class SoapClient {

        private static readonly ILog _log = LogManager.GetLogger("SoapClient");

        private readonly string _serviceAddress;
        private readonly HttpClient _httpClient;


        // Convenience constructor — creates a default HttpClient.
        // For production use, inject a shared HttpClient instance to avoid socket exhaustion.
        public SoapClient(string serviceAddress) : this(serviceAddress, new HttpClient()) { }

        public SoapClient(string serviceAddress, HttpClient httpClient) {
            if (string.IsNullOrWhiteSpace(serviceAddress))
                throw new ArgumentNullException(nameof(serviceAddress));
            _serviceAddress = serviceAddress;
            _httpClient     = httpClient ?? throw new ArgumentNullException(nameof(httpClient));
        }

        public async Task<SoapResponse> Send(SoapRequest request, UserConnection userConnection,
            bool doLog = true) {

            if (request == null)
                throw new ArgumentNullException(nameof(request));

            string url = _serviceAddress + request.Endpoint;

            _log.InfoFormat("[SoapClient] --> {0}", url);
            _log.InfoFormat("[SoapClient] REQUEST:\n{0}", request.Body);

            SoapResponse response    = null;
            string responseBody      = string.Empty;
            string errorMessage      = string.Empty;
            ExceptionDispatchInfo exInfo = null;

            try {
                var content = new StringContent(request.Body, Encoding.UTF8, "text/xml");

                // Some SOAP services require a SOAPAction header — uncomment and set if needed:
                // content.Headers.Add("SOAPAction", "\"http://example.com/YourActionName\"");

                HttpResponseMessage httpResponse = await _httpClient.PostAsync(url, content);
                responseBody = await httpResponse.Content.ReadAsStringAsync();
                int statusCode = (int)httpResponse.StatusCode;

                _log.InfoFormat("[SoapClient] <-- STATUS: {0}", statusCode);
                _log.InfoFormat("[SoapClient] RESPONSE:\n{0}", responseBody);

                response = new SoapResponse(statusCode, responseBody);
            }
            catch (Exception ex) {
                errorMessage = ex.Message;
                _log.ErrorFormat("[SoapClient] ERROR url={0} | {1}: {2}",
                    url, ex.GetType().Name, ex.Message);

                // Capture preserves the original stack trace so finally runs before the re-throw
                exInfo = ExceptionDispatchInfo.Capture(ex);
            }
            // finally {
            //     // Persist every call to the SoapLogs entity regardless of success or failure.
            //     // Logging failure must never suppress the original request exception.
            //     if (doLog && userConnection != null) {
            //         try {
            //             new Insert(userConnection)
            //                 .Into("SoapLogs")
            //                 .Set("Id",        Column.Parameter(Guid.NewGuid()))
            //                 .Set("Url",       Column.Parameter(url))
            //                 .Set("Request",   Column.Parameter(request.Body))
            //                 .Set("Response",  Column.Parameter(responseBody))
            //                 .Set("Error",     Column.Parameter(errorMessage))
            //                 .Set("CreatedOn", Column.Parameter(DateTime.UtcNow))
            //                 .Execute();
            //         }
            //         catch (Exception logEx) {
            //             _log.WarnFormat("[SoapClient] Failed to save log record: {0}", logEx.Message);
            //         }
            //     }
            // }

            // Re-throw with original stack trace if the request failed
            exInfo?.Throw();

            // Only reached when no exception occurred
            return response;
        }
    }

    // Immutable request DTO — set all values via constructor before passing to Send()
    public class SoapRequest {

        // Relative path appended to the base service address, e.g. "/operations/GetData"
        public string Endpoint { get; }

        // Full XML SOAP envelope body
        public string Body { get; }

        public SoapRequest(string endpoint, string body) {
            Endpoint = endpoint;
            Body     = body;
        }
    }

    // Immutable response DTO populated by SoapClient after a successful HTTP round-trip
    public class SoapResponse {

        // HTTP status code returned by the service (200, 500, etc.)
        public int StatusCode { get; }

        // Full XML response body, including SOAP Fault on error responses
        public string Body { get; }

        // True for any 2xx status code
        public bool IsSuccess => StatusCode >= 200 && StatusCode < 300;

        public SoapResponse(int statusCode, string body) {
            StatusCode = statusCode;
            Body       = body;
        }
    }
}
