define(function (require) {
	var $ = require('jQuery');
	var Backbone = require('Backbone');
	var hbs = require('hbs!./../templates/EmptyView');

	return Backbone.View.extend({
		template: hbs,
		tagName: 'section',
		className: 'empty-state',

		render: function () {
			this.$el.html(this.template(this.model ? this.model.toJSON() : {}));
			return this;
		}
	});
});
