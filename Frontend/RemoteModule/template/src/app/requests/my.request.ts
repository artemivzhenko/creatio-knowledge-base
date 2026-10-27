import { BaseRequest } from '@creatio-devkit/common';

export const MY_REQUEST = 'usr.MyRequest';

/**
 * A custom request raised from a page button:
 *   "clicked": { "request": "usr.MyRequest", "params": { "recordId": "$Id" } }
 *
 * Every `params` key arrives as a property of the request. There is no public
 * registration decorator for requests in @creatio-devkit/common: the class only
 * types the payload, the `request` string in the schema is what routes it.
 */
export class MyRequest extends BaseRequest {
  /** Id of the record to work with. */
  public recordId?: string;
}
