// --- Module schemas: CSS modules and custom view elements --------------------
// properties.json -> "SchemaType": "Module" covers two very different things.
//
// 1. CSS-ONLY MODULE
//    The .js file is EMPTY; the styles live next to it as a .css/.less resource
//    of the same schema. You consume it by adding "css!<ModuleName>" to the
//    dependency list of a page or detail:
//
//      define("QSOrder1Page", ["ProcessModuleUtilities", "css!QSOrder1PageStyle"],
//          function(ProcessModuleUtilities) { ... });
//
//    The "css!" plugin passes NO argument to the factory, so keep it last in the
//    array and the remaining arguments stay aligned.
//
//    Naming in this codebase: <Schema>CSS or <Schema>Style, e.g.
//    QSOrder1PageStyle, QSAdditionalServicesCSS, QSSchema9ca4f0c6DetailCSS.
//
//    Scope your selectors. A CSS module is loaded globally once any schema that
//    depends on it is opened, and it stays loaded for the rest of the session -
//    an unscoped rule will leak into other pages. Prefix with the schema id, for
//    example #QSSchemae4bc4d68DetailDetailControlGroup .my-class.
//
// 2. CUSTOM VIEW ELEMENT (web component)
//    A Module schema can define a custom HTML element and register it through
//    @creatio-devkit/common so Freedom UI pages can use it by type name. The
//    example below is the iframe wrapper from this package. This is Freedom UI
//    interop: a Classic UI page cannot place such an element through diff.

define("QSIFrameComponent", ["@creatio-devkit/common"], function(sdk) {

	class QSIFrameComponent extends HTMLElement {

		constructor() {
			super();
			this._dom = this.attachShadow({ mode: "open" });
		}

		get src() {
			return this._frameConfig.src;
		}

		set src(value) {
			this.frameConfig = { src: value };
		}

		get frameConfig() {
			return this._frameConfig;
		}

		set frameConfig(value) {
			this._frameConfig = value;

			this._frameConfig.src    = this.frameConfig.src || "about:blank";
			this._frameConfig.height = this.frameConfig.height || "100%";
			this._frameConfig.width  = this.frameConfig.width || "100%";

			this._frameConfig.style = (this._frameConfig.style || "") +
				"height:" + this.frameConfig.height + ";width:" + this.frameConfig.width + ";";
			if (!this.frameConfig.border) {
				this._frameConfig.style += "border:none;";
			}

			// Keep the sandbox attribute explicit; an iframe without it inherits
			// nothing and most embedded apps break.
			if (!this._frameConfig.sandbox) {
				this._frameConfig.sandbox = "allow-scripts allow-same-origin " +
					"allow-downloads allow-forms allow-popups allow-popups-to-escape-sandbox";
			}
			this._loadFrame();
		}

		_loadFrame() {
			this._dom.innerHTML =
				'<iframe src="' + this._frameConfig.src + '" ' +
				'style="' + this._frameConfig.style + '" ' +
				'sandbox="' + this._frameConfig.sandbox + '" ' +
				'allowfullscreen="" loading="lazy" ' +
				'referrerpolicy="no-referrer-when-downgrade"></iframe>';
		}
	}

	// 1. Register the element with the browser.
	customElements.define("usr-frame-component", QSIFrameComponent);

	// 2. Register it with Creatio so a page can reference type "usr.FrameComponent".
	//    `inputs` lists the properties bindable from the page config.
	sdk.registerViewElement({
		type: "usr.FrameComponent",
		selector: "usr-frame-component",
		inputs: {
			frameConfig: {},
			src: {}
		}
	});

	return QSIFrameComponent;
});
