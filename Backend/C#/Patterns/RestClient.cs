using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;
using global::Common.Logging;
using Newtonsoft.Json;

/// <summary>
/// Pattern: generic REST API client covering all standard HTTP methods.
/// REST counterpart to SoapClient — use this for JSON APIs, SoapClient for XML/SOAP.
///
/// Supports: GET, POST, PUT, PATCH, DELETE
/// Each verb has an async and a sync variant; typed overloads handle JSON deserialization.
///
/// Authentication: optional API key sent as a request header on every call.
/// For Bearer tokens pass headerName = "Authorization" and apiKey = "Bearer {token}".
///
/// For production: inject a shared HttpClient to avoid socket exhaustion under load.
/// </summary>
namespace Terrasoft.Configuration {

    public class RestClient {

        private static readonly ILog _log = LogManager.GetLogger("RestClient");

        private static readonly HttpMethod PatchMethod = new HttpMethod("PATCH");

        private readonly HttpClient _httpClient;
        private readonly string     _baseUrl;

        // No authentication
        public RestClient(string baseUrl) : this(baseUrl, null) { }

        // API key / Bearer token authentication
        // headerName examples: "X-Api-Key", "Authorization"
        // apiKey examples:     "my-secret-key", "Bearer eyJhbGci..."
        public RestClient(string baseUrl, string apiKey, string headerName = "X-Api-Key") {
            if (string.IsNullOrWhiteSpace(baseUrl))
                throw new ArgumentNullException(nameof(baseUrl));

            _baseUrl    = baseUrl.TrimEnd('/');
            _httpClient = new HttpClient();

            if (!string.IsNullOrEmpty(apiKey))
                _httpClient.DefaultRequestHeaders.Add(headerName, apiKey);
        }

        // ── GET ───────────────────────────────────────────────────────────────

        public async Task<string> GetAsync(string endpoint,
            Dictionary<string, string> queryParams = null) {
            return await ExecuteAsync(HttpMethod.Get, ComposeUrl(endpoint, queryParams));
        }

        public async Task<T> GetAsync<T>(string endpoint,
            Dictionary<string, string> queryParams = null) where T : class {
            return Deserialize<T>(await GetAsync(endpoint, queryParams));
        }

        public string Get(string endpoint, Dictionary<string, string> queryParams = null) {
            return Sync(() => GetAsync(endpoint, queryParams));
        }

        public T Get<T>(string endpoint,
            Dictionary<string, string> queryParams = null) where T : class {
            return Sync(() => GetAsync<T>(endpoint, queryParams));
        }

        // ── POST ──────────────────────────────────────────────────────────────

        public async Task<string> PostAsync(string endpoint, string jsonBody) {
            return await ExecuteAsync(HttpMethod.Post, ComposeUrl(endpoint), jsonBody);
        }

        public async Task<T> PostAsync<T>(string endpoint, object payload) where T : class {
            return Deserialize<T>(await PostAsync(endpoint, Serialize(payload)));
        }

        public string Post(string endpoint, string jsonBody) {
            return Sync(() => PostAsync(endpoint, jsonBody));
        }

        public T Post<T>(string endpoint, object payload) where T : class {
            return Sync(() => PostAsync<T>(endpoint, payload));
        }

        // ── PUT ───────────────────────────────────────────────────────────────

        public async Task<string> PutAsync(string endpoint, string jsonBody) {
            return await ExecuteAsync(HttpMethod.Put, ComposeUrl(endpoint), jsonBody);
        }

        public async Task<T> PutAsync<T>(string endpoint, object payload) where T : class {
            return Deserialize<T>(await PutAsync(endpoint, Serialize(payload)));
        }

        public string Put(string endpoint, string jsonBody) {
            return Sync(() => PutAsync(endpoint, jsonBody));
        }

        public T Put<T>(string endpoint, object payload) where T : class {
            return Sync(() => PutAsync<T>(endpoint, payload));
        }

        // ── PATCH ─────────────────────────────────────────────────────────────

        public async Task<string> PatchAsync(string endpoint, string jsonBody) {
            return await ExecuteAsync(PatchMethod, ComposeUrl(endpoint), jsonBody);
        }

        public async Task<T> PatchAsync<T>(string endpoint, object payload) where T : class {
            return Deserialize<T>(await PatchAsync(endpoint, Serialize(payload)));
        }

        public string Patch(string endpoint, string jsonBody) {
            return Sync(() => PatchAsync(endpoint, jsonBody));
        }

        public T Patch<T>(string endpoint, object payload) where T : class {
            return Sync(() => PatchAsync<T>(endpoint, payload));
        }

        // ── DELETE ────────────────────────────────────────────────────────────

        public async Task<string> DeleteAsync(string endpoint) {
            return await ExecuteAsync(HttpMethod.Delete, ComposeUrl(endpoint));
        }

        public async Task<T> DeleteAsync<T>(string endpoint) where T : class {
            return Deserialize<T>(await DeleteAsync(endpoint));
        }

        public string Delete(string endpoint) {
            return Sync(() => DeleteAsync(endpoint));
        }

        public T Delete<T>(string endpoint) where T : class {
            return Sync(() => DeleteAsync<T>(endpoint));
        }

        // ── Internal ──────────────────────────────────────────────────────────

        // Single execution path for all verbs — logs request/response, handles errors uniformly
        private async Task<string> ExecuteAsync(HttpMethod method, string url,
            string jsonBody = null) {

            _log.InfoFormat("[RestClient] {0} {1}", method.Method, url);
            try {
                var request = new HttpRequestMessage(method, url);
                if (jsonBody != null)
                    request.Content = new StringContent(jsonBody, Encoding.UTF8, "application/json");

                HttpResponseMessage response = await _httpClient.SendAsync(request);
                string body = await response.Content.ReadAsStringAsync();

                _log.InfoFormat("[RestClient] {0} {1} -> {2}",
                    method.Method, url, (int)response.StatusCode);
                return body;
            }
            catch (Exception ex) {
                _log.ErrorFormat("[RestClient] {0} {1} failed: {2}",
                    method.Method, url, ex.Message);
                throw;
            }
        }

        private string ComposeUrl(string endpoint,
            Dictionary<string, string> queryParams = null) {

            string url = _baseUrl + "/" + endpoint.TrimStart('/');
            if (queryParams == null || queryParams.Count == 0)
                return url;

            var sb = new StringBuilder();
            foreach (var kv in queryParams) {
                if (sb.Length > 0) sb.Append('&');
                sb.Append(Uri.EscapeDataString(kv.Key));
                sb.Append('=');
                sb.Append(Uri.EscapeDataString(kv.Value ?? string.Empty));
            }
            return url + "?" + sb;
        }

        private static string Serialize(object obj) {
            return JsonConvert.SerializeObject(obj);
        }

        private static T Deserialize<T>(string json) where T : class {
            return string.IsNullOrEmpty(json) ? null : JsonConvert.DeserializeObject<T>(json);
        }

        // Sync wrapper — blocks current thread; use only where async is unavailable (Script Tasks)
        private static T Sync<T>(Func<Task<T>> action) {
            return Task.Run(action).GetAwaiter().GetResult();
        }
    }
}
