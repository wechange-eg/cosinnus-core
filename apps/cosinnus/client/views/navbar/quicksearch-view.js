'use strict';

var BaseView = require('views/base/view');
var util = require('lib/util');

module.exports = BaseView.extend({

    app: null,

    template: require('navbar/quicksearch'),

    fetchURL: '/search/api/quicksearch/',

    // the parent el, containing the search textbox and button
    $searchBarEl: null,

    // will be set to self.options during initialization
    defaults: {
        query: null,
        searchMethods: {
            'default': '/search/?q={{q}}',
            'map': '/map/?q={{q}}',
            'groups': '/search/?groups=mine&q={{q}}',
            'cloudfiles': '/search/cloudfiles/?q={{q}}'
        },
        topicsSearchMethods: {
            // <title>: <url>,
        },
        // this will be added to the state.topicsSearchMethods for matching topics
        topicsUrl: '/map/?topics={{t}}',
        sdgSearchMethods: {},
        sdgsUrl: '/map/?sdgs={{t}}',

        state: {
            loading: false, // if true, a request is currently loading
            currentRequest: null, // the XMLHttpRequest that is currently loading
            hadErrors: false,

            quicksearchResults: [],

            fireQuicksearchTimeout: null
        }
    },

    // The DOM events specific to an item.
    events: {
    },

    initialize: function (options, app) {
        var self = this;
        self.app = app;
        BaseView.prototype.initialize.call(self, options);

        self.$searchBarEl = $('#nav-quicksearch');
        // events that have to be defined here because they happen in the searchBarEl:
        self.$searchBarEl.on('focus', '.nav-search-box', self.thisContext(self.onSearchBoxFocusIn));
        self.$searchBarEl.on('keydown', '.nav-search-box', self.thisContext(self.onSearchBoxKeyDown));
        self.$searchBarEl.on('input', '.nav-search-box', self.thisContext(self.onSearchBoxTyped));
        self.$searchBarEl.on('click', '.nav-button-search', self.thisContext(self.onSearchIconClicked));
        self.$searchBarEl.on('click', '.quicksearch-filterbutton', self.thisContext(self.onQuickSearchFilterButtonClicked));


        // TODO: add a collection for quicksearch DB results!
        return;

        // result events
        self.collection.on({
            'add': self.thisContext(self.tileAdd),
            'change': self.thisContext(self.tileUpdate),
            'remove': self.thisContext(self.tileRemove),
            'update': self.thisContext(self.tilesUpdate),
            'reset': self.thisContext(self.tilesReset),
        });

    },

    render: function () {
        var self = this;
        BaseView.prototype.render.call(self);

        util.log('*** Rendered quicksearch! ***')
        this.$searchBarEl.find('.dropdown-underdrop').height(this.$el.outerHeight());
        return self;
    },

    /** Extend the template data by the controlView's options and state */
    getTemplateData: function () {
        var self = this;
        var data = BaseView.prototype.getTemplateData.call(self);
        return data;
    },

    /** Searchbox focused */
    onSearchBoxFocusIn: function (event) {
        this.$searchBarEl.find('.nav-search-box').attr('placeholder', this.options.placeholder);
        this.showDropdown();
    },

    /** Searchbox key downs, for special keys */
    onSearchBoxKeyDown: function (event) {
        if (event.keyCode == 13) {
            this.fireSearch();
        } else if (event.keyCode == 27) {
            this.$searchBarEl.removeClass('active').find('.nav-search-box').blur();
            $('.v2-navbar').removeClass('search-open');
        }
    },

    onQuickSearchFilterButtonClicked: function (event) {
        event.preventDefault();
        var type = event.currentTarget.getAttribute('data-result-filter-type');
        var query = this.getCurrentQuery();

        var data = {
            'q': query ? query : '',
            'people': type === 'people',
            'events': type === 'events',
            'projects': type === 'projects',
            'groups': type === 'groups',
            'ideas': type === 'ideas',
            'conferences': type === 'conferences',
            'organizations': type === 'organizations'
        };

        var params = [];

        for (var d in data) {
            params.push(encodeURIComponent(d) + '=' + encodeURIComponent(data[d]));
        }
        var url = '/map/?' + params.join('&');
        window.location.href = url;
    },

    /** Searchbox text input */
    onSearchBoxTyped: function (event) {
        var self = this;
        if (!event.shiftKey && !event.ctrlKey) {
            if (self.state.fireQuicksearchTimeout !== null) {
                // prevent the quicksearch request from being started
                clearTimeout(self.state.fireQuicksearchTimeout);
            }
            this.updateSearchSuggestions();
        }
    },

    /** rerenders the list of clickable search suggestions, e.g. after new input was made */
    updateSearchSuggestions: function () {
        var self = this;
        var query = self.getCurrentQuery();

        // apply the current query to the urls in searchMethods
        var searchMethods = _(self.options.searchMethods).clone();
        for (var method in searchMethods) {
            searchMethods[method] = searchMethods[method].replace('{{q}}', encodeURIComponent(query));
        }
        self.state.searchMethods = searchMethods;
        // match topics to the current query and generate topic search suggestions
        var topicsSearchMethods = {};
        for (var topicId in self.options.topicsJson) {
            var topic = self.options.topicsJson[topicId];
            if (topic && topic.toLowerCase().indexOf(query.toLowerCase()) > -1) {
                // highlight the topic occurence
                var title = util.iReplace(topic, query, '<b>$1</b>');
                var url = self.options.topicsUrl.replace('{{t}}', topicId);
                topicsSearchMethods[title] = url;
            }
        }

        if (self.options.sdgsJson.length > 0) {
            var sdgSearchMethods = {};
            for (var sdgId in self.options.sdgsJson) {
                var sdg = self.options.sdgsJson[sdgId];
                if (sdg && sdg.name.toLowerCase().indexOf(query.toLowerCase()) > -1) {
                    var title = util.iReplace(sdg.name, query, '<b>$1</b>')
                    var url = self.options.sdgsUrl.replace('{{t}}', sdg.id);
                    sdgSearchMethods[title] = url;
                }
            }
        }


        self.state.topicsSearchMethods = topicsSearchMethods
        self.state.sdgSearchMethods = sdgSearchMethods

        self.state.query = query || null;
        self.state.quicksearchResults = [];
        self.render();

        if (self.state.query && self.state.query.length > 2) {
            // wait a short time before issuing a HTTP request, 
            // in case the user types more stuff in the meantime;
            // in that case, the timeout will be cleared/cancelled.
            self.state.fireQuicksearchTimeout = setTimeout(self.loadQuickResults, 300, self, self.state.query);
        }
    },

    /** Get the text from the search box */
    getCurrentQuery: function () {
        return this.$searchBarEl.find('.nav-search-box').val().trim();
    },

    /** Fire off a search. If no arguments given, fires the default search
     * 	with the currently entered text */
    fireSearch: function (type, query) {
        var self = this;
        if (!type) {
            type = 'default';
        }
        if (!query) {
            query = self.getCurrentQuery();
        }
        if (query && query.length > 0) {
            var url = self.options.searchMethods[type].replace('{{q}}', encodeURIComponent(query));
            window.location = url;
        }
    },

    /** Shows the quicksearch result list */
    showDropdown: function () {
        util.log('*** Showing quicksearch results ***')
        document.addEventListener('click', this.thisContext(this.checkQuickSearchFocusOut));
        this.$searchBarEl.addClass('active');
        $('.v2-navbar').addClass('search-open');
        this.render();
    },

    /** Hides the quicksearch result list */
    hideDropdown: function () {
        util.log('*** Hiding quicksearch results ***')
        this.$el.hide();
    },

    /** While we are focused, check for clicks outside to trigger closing the menu */
    checkQuickSearchFocusOut: function (event) {
        if ((this.$searchBarEl.hasClass('active') && !this.$searchBarEl[0].contains(event.target))
            || $(event.target).hasClass('nav-search-backdrop')) {
            this.$searchBarEl.removeClass('active');
            $('.v2-navbar').removeClass('search-open');
            this.$searchBarEl.find('.nav-search-box').attr('placeholder', '');
            document.removeEventListener('click', this.thisContext(this.checkQuickSearchFocusOut));
        }
    },

    onSearchIconClicked: function (event) {
        if (this.$searchBarEl.hasClass('active')) {
            this.fireSearch();
        } else {
            this.$searchBarEl.find('.nav-search-box').attr('placeholder', this.options.placeholder);
            this.$searchBarEl.find('.nav-search-box').focus();
        }
    },

    /** Quicksearch results data fetch logic */

    /** Loads a new set of quicksearch results for the given query.
     *  Calling this will cancel the currently running request, if existing. */
    loadQuickResults: function (self, query) {
        if (self.state.loading) {
            if (self.state.currentRequest !== null) {
                self.state.currentRequest.abort();
                self.state.currentRequest = null;
            }
            self.state.loading = false;
        }

        self.state.loading = true;
        //self.showLoadingPlaceholder();
        //self.hideErrorMessage();
        // using this instead of .finally() for backwards compatibility in browsers

        var finally_compat = function () {
            self.state.loading = false;
            //self.hideLoadingPlaceholder();
        };
        self.loadData(query).then(function (data) {
            util.log('# quicksearch received data and is now handling it');
            self.handleData(data);
            finally_compat();
        })/**.catch(function(message){
			self.handleError(message);
			finally_compat();
		})*/;
    },


    /** Loads a set of data from the server. Returns a promise
     *  whose resolve function gets passed the data */
    loadData: function (query) {
        var self = this;
        return new Promise(function (resolve, reject) {
            // build URL
            var url = self.fetchURL + '?' + $.param({ 'q': query });
            self.state.currentRequest = $.ajax(url, {
                type: 'GET',
                success: function (response, textStatus, xhr) {
                    if (xhr.status == 200) {
                        resolve(response['data']);
                    } else {
                        reject(xhr.statusText);
                    }
                },
                error: function (xhr, textStatus) {
                    reject(textStatus);
                },
                complete: function () {
                    self.state.currentRequest = null;
                }
            });
        });
    },

    handleData: function (data) {
        var self = this;
        util.log('# # Fetched data for quicksearch');

        // display items if any
        if (data['count'] > 0) {
            self.state.quicksearchResults = data['items'];
            $.each(self.state.quicksearchResults, function (itemIdx, item) {
                // we expect escaped text here! 
                // otherwise, we could make it safe using: var text = $('<div>').text(item['text']).html();
                var text = item['text'];
                $.each(self.state.query.split(' '), function (queryTermIdx, queryTerm) {

                    text = util.iReplace(text, queryTerm, '<b>$1</b>');
                });
                item['text'] = text;
                if (typeof (item.subtext) === "string") {
                    var subtext = item.subtext;
                    $.each(self.state.query.split(' '), function (queryTermIdx, queryTerm) {
                        subtext = util.iReplace(subtext, queryTerm, '<b>$1</b>');
                    });
                    item.subtext = subtext;
                }
            });
            self.render();
        }
    },

    handleError: function (message) {
        var self = this;
        util.log('# Error during quicksearch request!');
        //self.showErrorMessage();
    },

});
