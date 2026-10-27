import { BaseRequest, CrtRequest } from '@creatio/mobile-common';

export const MY_REQUEST = 'usr.MyRequest';

/**
 * A custom request raised from a page button:
 *   "clicked": { "request": "usr.MyRequest", "params": { "attributeName": "PDS_UsrName_a1b2c3d" } }
 *
 * Keep every parameter optional: params delivery on mobile pages is
 * undocumented, so the handler must work when they do not arrive.
 */
@CrtRequest({
	type: MY_REQUEST,
})
export class UsrMyRequest extends BaseRequest {
	/** Page attribute to work with; the handler falls back to a default when absent. */
	public attributeName?: string;
}
