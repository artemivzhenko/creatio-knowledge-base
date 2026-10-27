/* Import the required functionality from the libraries. */
import { DoBootstrap, Injector, NgModule, ProviderToken } from '@angular/core';
import { createCustomElement } from '@angular/elements';
import { BrowserModule } from '@angular/platform-browser';
import { bootstrapCrtModule, CrtModule } from '@creatio-devkit/common';
import { InputComponent } from './view-elements/input/input.component';
import { MyRequestHandler } from './handlers/my-request.handler';
import { PageInitHandler } from './handlers/page-init.handler';

@CrtModule({
  /* Specify that InputComponent is a view element. */
  viewElements: [InputComponent],
  /* Request handlers run in the pages listed in their `scopes`. */
  requestHandlers: [MyRequestHandler, PageInitHandler],
})

@NgModule({
  declarations: [
    InputComponent
  ],
  imports: [BrowserModule],
  providers: [],
})
export class AppModule implements DoBootstrap {
  constructor(private _injector: Injector) {}

  ngDoBootstrap(): void {
    /* Register InputComponent as an Angular Element. */
    const element = createCustomElement(InputComponent, {
      injector: this._injector,
    });
    customElements.define('usr-input', element);
    
    /* Bootstrap CrtModule definitions. */
    bootstrapCrtModule('sdk_remote_module_package', AppModule, {
      resolveDependency: (token) => this._injector.get(<ProviderToken<unknown>>token)
    });
  }
}