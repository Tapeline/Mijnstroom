require.config({
	hbs: {
		templateExtension: 'html',
		disableI18n: true,
		disableHelpers: true
	},

	shim: {
		'jQuery': {
			exports: '$'
		},

		'Underscore': {
			exports: '_'
		},

		'Backbone': {
			deps: ['Underscore', 'jQuery'],
			exports: 'Backbone'
		},

		'Handlebars': {
			deps: ['handlebars'],
			exports: 'Handlebars'
		},

		'ApplicationRouter': {
			deps: ['jQuery', 'Underscore', 'Backbone']
		}
	},

	paths: {
		jQuery: './../vendored/jquery.min',
		Underscore: './../vendored/underscore-min',
		underscore: './../vendored/require-handlebars-plugin/hbs/underscore',
		Backbone: './../vendored/backbone-min',
		handlebars: './../vendored/require-handlebars-plugin/Handlebars',
		hbs: './../vendored/require-handlebars-plugin/hbs',
		i18nprecompile : './../vendored/require-handlebars-plugin/hbs/i18nprecompile',
		json2 : './../vendored/require-handlebars-plugin/hbs/json2'
	}
});

require(
  ['core/router', 'core/client', 'Backbone'],
  function (Router, client, Backbone) {
    var app = {
      root: '/'
    };

    window.Router = new Router();
    client.setup(window, app);

    Backbone.history.start({ hashChange: true });
  }
);
