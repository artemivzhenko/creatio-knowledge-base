/**
 * Freedom UI pages (schema codes) the handlers run in.
 *
 * An empty array, or no `scopes` at all, makes a handler global: it runs on
 * every Freedom UI page of the application. For crt.* platform requests such
 * as crt.HandleViewModelInitRequest that means every page load in the system.
 */
export const PAGE_SCOPES: string[] = ['UsrMyPage_FormPage'];
