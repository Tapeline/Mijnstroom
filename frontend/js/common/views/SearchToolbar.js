define(function (require) {
	var $ = require('jQuery');
	var Backbone = require('Backbone');
	var hbs = require('hbs!./../templates/SearchToolbar');

	return Backbone.View.extend({
		template: hbs,
		tagName: 'div',
		className: 'search-toolbar',

		events: {
			'keydown .js-search': 'onSearch',
			'click .js-clear': 'onClear',
			'click .js-include-unset': 'onToggleUnset'
		},

		initialize: function (options) {
			this.filters = options.filters || { include_unset: false };
			this.onFilter = options.onFilter || function () {};
		},

		render: function () {
			this.$el.html(this.template(this.filters));
			return this;
		},

		onSearch: function (e) {
			if (e.which === 13) {
				var field = $(e.currentTarget).data('field');
				this.filters[field] = $(e.currentTarget).val().trim() || null;
				this.onFilter(this.filters);
			}
		},

		onClear: function () {
			this.filters = { include_unset: this.filters.include_unset || false };
			this.$('.js-search').val('');
			this.onFilter(this.filters);
		},

		onToggleUnset: function () {
			this.filters.include_unset = this.$('.js-include-unset').is(':checked');
			this.onFilter(this.filters);
		}
	});
});
