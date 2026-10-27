import { BaseRequest, BaseRequestHandler, CrtRequestHandler, Logger } from '@creatio/mobile-common';

/**
 * Diagnostic handler: prints the scopes the platform reports for the current page.
 *
 * The mapping between a page schema name and the scope string is undocumented.
 * To learn the exact value: register this handler in @CrtModule (src/index.ts),
 * `npm run build:inject-on-device`, restart the app, open the page and read
 *   [UsrMobileModule] scopes on crt.LoadDataRequest: ["UsrMyEntity_MobileFormPage"]
 * in chrome://inspect. Copy the value into PAGE_SCOPES and REMOVE this handler
 * again: with `scopes: []` it fires on every page of the app.
 */
@CrtRequestHandler({
	type: 'usr.ScopeProbeRequestHandler',
	requestType: 'crt.LoadDataRequest',
	scopes: [],
})
export class UsrScopeProbeRequestHandler extends BaseRequestHandler {
	public async handle(request: BaseRequest): Promise<unknown> {
		Logger.console(`[UsrMobileModule] scopes on ${request.type}: ${JSON.stringify(request.scopes)}`);
		return this.next?.handle(request);
	}
}
