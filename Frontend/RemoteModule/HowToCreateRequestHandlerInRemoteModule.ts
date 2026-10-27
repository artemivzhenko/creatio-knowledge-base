// --- How to create a Freedom UI request handler in an Angular remote module ---
// A request handler can live in the remote module instead of a page schema's
// `handlers` section (Creatio 8.0.8+). One TypeScript class then serves every
// page listed in its `scopes`, can intercept platform crt.* requests, and gets
// Angular services through constructor injection. The working project is the
// folder next to this file, Frontend/RemoteModule/template/ (src/app/handlers,
// requests, services); project setup itself is in
// HowToCreateCustomAngularViewElement.
//
// Traps:
// - Empty or missing `scopes` makes the handler global: it runs on every
//   Freedom UI page of the application. For crt.HandleViewModelInitRequest
//   that is every page load in the system.
// - A handler only exists once it is listed in `requestHandlers` of @CrtModule.
//   The decorator alone registers nothing.
// - Constructor injection works only because bootstrapCrtModule() is given
//   `resolveDependency` backed by the module injector. Drop that option and
//   the injected service arrives as undefined.
// - @creatio-devkit/common has no public decorator for requests: a custom
//   request class only types the payload. The `request` string in the page
//   schema routes it, and every `params` key arrives as a request property.
// - In a platform-request handler, call `this.next` first when your logic needs
//   an initialized view model; calling it last runs your code before the page
//   has its attributes and data sources.
// - A value written to `request.$context['X']` only reaches the page if the
//   page declares attribute X in viewModelConfigDiff. An undeclared attribute
//   is ignored without an error.
// - Return `this.next?.handle(request)` unless you replace the platform
//   behaviour on purpose; skipping it silently disables the stock handler and
//   every handler registered after yours.

// ===== file: src/app/handlers/scopes.ts =====
export const PAGE_SCOPES: string[] = ['UsrMyPage_FormPage'];

// ===== file: src/app/requests/my.request.ts =====
import { BaseRequest } from '@creatio-devkit/common';

export const MY_REQUEST = 'usr.MyRequest';

export class MyRequest extends BaseRequest {
  public recordId?: string;
}

// ===== file: src/app/services/my-data.service.ts =====
import { Injectable } from '@angular/core';
import { HttpClientService } from '@creatio-devkit/common';

export interface MyDataResponse {
  value: string;
}

/** HttpClientService sends the current user's session, so /rest/... hits this site. */
@Injectable({ providedIn: 'root' })
export class MyDataService {
  private readonly _http = new HttpClientService();

  public async getValue(recordId: string): Promise<string> {
    const response = await this._http.post<MyDataResponse>(
      '/rest/UsrMyService/GetValue',
      { recordId },
      {},
    );
    return response.body?.value ?? '';
  }
}

// ===== file: src/app/handlers/my-request.handler.ts =====
import { BaseRequestHandler, CrtRequestHandler } from '@creatio-devkit/common';

@CrtRequestHandler({
  type: 'usr.MyRequestHandler',
  requestType: MY_REQUEST,
  scopes: PAGE_SCOPES,
})
export class MyRequestHandler extends BaseRequestHandler<MyRequest> {
  constructor(private readonly _dataService: MyDataService) {
    super();
  }

  public async handle(request: MyRequest): Promise<unknown> {
    const recordId = request.recordId ?? await request.$context['Id'];
    const value = await this._dataService.getValue(recordId);
    request.$context['UsrMyValue'] = value;
    return this.next?.handle(request);
  }
}

// ===== file: src/app/handlers/page-init.handler.ts =====
/** Raises usr.MyRequest on page load, after the platform initialized the view model. */
@CrtRequestHandler({
  type: 'usr.PageInitHandler',
  requestType: 'crt.HandleViewModelInitRequest',
  scopes: PAGE_SCOPES,
})
export class PageInitHandler extends BaseRequestHandler {
  public async handle(request: BaseRequest): Promise<unknown> {
    const result = await this.next?.handle(request);
    await this.handlerChain.process({
      type: MY_REQUEST,
      $context: request.$context,
    } as BaseRequest);
    return result;
  }
}

// ===== file: src/app/app.module.ts (only the registration) =====
// @CrtModule({
//   viewElements: [InputComponent],
//   requestHandlers: [MyRequestHandler, PageInitHandler],
// })
// ...
// bootstrapCrtModule('sdk_remote_module_package', AppModule, {
//   resolveDependency: (token) => this._injector.get(<ProviderToken<unknown>>token),
// });

// ===== page schema: UsrMyPage_FormPage =====
// viewModelConfigDiff - the attribute the handler writes:
// { "operation": "merge", "path": ["attributes"], "values": { "UsrMyValue": {} } }
//
// viewConfigDiff - a label showing it, and a button raising the request:
// {
//   "operation": "insert",
//   "name": "UsrMyValueLabel",
//   "values": { "type": "crt.Label", "caption": "$UsrMyValue" },
//   "parentName": "SideAreaProfileContainer",
//   "propertyName": "items",
//   "index": 0
// },
// {
//   "operation": "insert",
//   "name": "UsrMyButton",
//   "values": {
//     "type": "crt.Button",
//     "caption": "Refresh",
//     "clicked": { "request": "usr.MyRequest", "params": { "recordId": "$Id" } }
//   },
//   "parentName": "ActionButtonsContainer",
//   "propertyName": "items",
//   "index": 0
// }
