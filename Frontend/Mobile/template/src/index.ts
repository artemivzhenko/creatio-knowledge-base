import { bootstrapCrtModule, CrtModule, DoBootstrap } from '@creatio/mobile-common';
import { UsrMyRequestHandler } from './handlers/my-request.handler';
import { UsrAttributeChangeRequestHandler } from './handlers/attribute-change.handler';

export * from './requests/my-request';
export * from './handlers/my-request.handler';
export * from './handlers/attribute-change.handler';

/**
 * Remote module entry point.
 *
 * The class name and the string passed to bootstrapCrtModule() must equal
 * `moduleName` in creatio-mobile-config.json: the bundle is served from
 *   <package>/Files/src/mobile/<moduleName>/main.js
 * and nothing reports a mismatch - the module just never loads.
 *
 * UsrScopeProbeRequestHandler is intentionally NOT listed: register it only
 * while learning the scope value, then remove it again.
 */
@CrtModule({
	requestHandlers: [
		UsrMyRequestHandler,
		UsrAttributeChangeRequestHandler,
	],
})
export class UsrMobileModule implements DoBootstrap {
	public bootstrap(): void {
		bootstrapCrtModule('UsrMobileModule', UsrMobileModule);
	}
}
