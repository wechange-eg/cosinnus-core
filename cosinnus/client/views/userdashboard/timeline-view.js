'use strict';

var BaseView = require('views/base/view');
var util = require('lib/util');

module.exports = BaseView.extend({

	app: null,
    template: require('userdashboard/timeline'),
    
    fetchURL: '/dashboard/api/timeline/',
    
    uiPrefsView: null, // set during initialization
    
    // will be set to self.options during initialization
    defaults: {
        
    	onlyMine: false, // inited from uiPrefs
    	
        state: {
        	loading: false, // if true, a request is currently loading
            currentRequest: null, // the XMLHttpRequest that is currently loading
            hadErrors: false,
            
            // load params. also initialized in `initializeParams`
    		itemsLoaded: 0,
    		offsetTimestamp: null,
    		hasMore: true,
        }
    },
    
    // The DOM events specific to an item.
    events: {
    	//'focus .nav-search-box': 'onSearchBoxFocusIn',
    	// todo: onlyMine button
    	'click .toggle-group-content-only': 'toggleOnlyMineClicked',
    	'click .retry-load': 'retryLoadAfterErrors',
    	'click .show-all-comments': 'showAllCommentsForItem',
    	'click .comment-form :not(textarea)': 'delegateTextInputClick',
    	'keypress .comment-form textarea': 'commentTextboxKeyPressed',
    },

    initialize: function (options, app, uiPrefsView) {
        var self = this;
        self.app = app;
        BaseView.prototype.initialize.call(self, options);
        
        self.uiPrefsView = uiPrefsView;
        self.options.onlyMine = self.uiPrefsView.getUiPref('timeline__only_mine');
        self.initializeParams();
        self.render();
    },
    
    initializeParams: function () {
    	var self = this;
    	self.state.itemsLoaded = 0;
    	self.state.offsetTimestamp = null;
    	self.state.hasMore = true;
    },
    
    getParamsForFetchRequest: function() {
    	var self = this;
    	var urlParams = {
			'only_mine': self.options.onlyMine,
    	};
    	if (self.state.offsetTimestamp) {
    		urlParams['offset_timestamp'] = self.state.offsetTimestamp;
    	}
    	return {urlSuffix: null, urlParams: urlParams}
    },

    render: function () {
        var self = this;
        BaseView.prototype.render.call(self);
        util.log('*** Rendered timeline! ***')
        return self;
    },
    
    /** Resets all timeline-items and loads from with fresh params */
    resetAndLoad: function () {
    	var self = this;
    	if (self.state.currentRequest) {
    		self.state.currentRequest.abort();
    		self.state.currentRequest = null;
    	}
    	self.state.loading = false;
    	self.state.hadErrors = false;
    	self.initializeParams();
    	self.render();
    	self.load();
    },
    
    /** Called from the "Retry" button shown with an error message */
    retryLoadAfterErrors: function () {
    	var self = this;
		self.state.hadErrors = false;
		self.load();
    },
    
    /** Called from a "show all comments" link from an item */
    showAllCommentsForItem: function (event) {
    	var self = this;
		var $target = $(event.target);
		$target.parents('.timeline-item-comments').find('.shown-when-more').hide();
		$target.parents('.timeline-item-comments').find('.comment-hidden').fadeIn();
    },
    
    /** Makes the i.fa icon clickable as if it were the textarea */
    delegateTextInputClick: function (event) {
    	$(event.target).parents('.comment-form').find('textarea').focus();
    },
    
    /** Pressing enter (unless with shift or ctrl) sends the form */
    commentTextboxKeyPressed: function (event) {
    	if (event.keyCode == 13 && !event.shiftKey && !event.ctrlKey) {
    	    var $form = $(event.target).parents('form');
    	    if (!$form.hasClass('disabled')) {
    	    	$form.submit();
    	    }
    	    event.preventDefault();
    	}
    },
    
    /** Call to load a new page of items from the current offset,
     *  will only fire a request if no other request is currently running */
    load: function () {
    	var self = this;
    	if (!self.state.loading && !self.state.hadErrors && self.state.hasMore) {
	    	return new Promise(function(resolve, reject) {
	    		self.state.loading = true;
	    		self.showLoadingPlaceholder();
	    		self.hideErrorMessage();
	    		// using this instead of .finally() for backwards compatibility in browsers
	    		var finally_compat = function() {
	    			self.state.loading = false;
	    			self.hideLoadingPlaceholder();
	    			resolve();
	    		};
	    		self.loadData().then(function(data){
	    			util.log('# timeline received data and will handle them');
	    			self.enableInfiniteScroll();
	    			self.handleData(data);
	    			finally_compat();
	    		}).catch(function(message){
	    			self.handleError(message);
	    			finally_compat();
	    		});
	    	});
    	}
    },
    
    /** Loads a set of data from the server. Returns a promise
     *  whose resolve function gets passed the data */
    loadData: function() {
    	var self = this;
		return new Promise(function(resolve, reject) {
			// build URL
			var params = self.getParamsForFetchRequest();
			var url = self.fetchURL + (params.urlSuffix ? params.urlSuffix + '/' : '');
			if (params.urlParams) {
				url += '?' + $.param(params.urlParams);
			}
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
                complete: function() {
                	self.state.currentRequest = null;
                }
            });
    	});
    },
    
    handleData: function (data) {
    	var self = this;
        util.log('# # Fetched data for timeline');
        util.log(data)
        
        // display items if any
        if (data['count'] > 0) {
        	self.renderLoadedItems(data['items']);
        }
        if (data['has_more'] == true) {
        	// set hasMore and offset
        	self.state.hasMore = true;
        	self.state.offsetTimestamp = data['last_timestamp'];
        } else {
        	// show final dot and disable infinitescroll if no hasMore
        	self.state.hasMore = false;
        	self.showFinalDot();
        	self.disableInfiniteScroll();
        }
    },
    
    renderLoadedItems: function (items) {
    	var self = this;
    	var timeline = self.$el.find('.timeline');
    	$.each(items, function(i, item){
    		timeline.append(item);
    	});

    	$.cosinnus.renderMomentDataDate();
		$.cosinnus.truncatedTextfield();
		self.removeEmptyDivs();
    },
    
    handleError: function (message) {
    	var self = this;
    	util.log('# # Fetched data for timeline');
    	self.disableInfiniteScroll();
    	self.showErrorMessage();
    },
    
    showErrorMessage: function (message) {
    	this.$el.find('.timeline-error-message').show();
    },
    
    hideErrorMessage: function () {
    	this.$el.find('.timeline-error-message').hide();
    },
    
    showLoadingPlaceholder: function () {
    	var topHeight = this.$el.height();
    	this.$el.find('.timeline-placeholder-frame').css({'top': topHeight}).show();
    },
    
    hideLoadingPlaceholder: function () {
    	this.$el.find('.timeline-placeholder-frame').hide();
    },
    
    showFinalDot: function () {
    	this.$el.find('.timeline-final-dot').show();
    },
    
    enableInfiniteScroll: function () {
    	var self = this;
        $(window).off('scroll').on('scroll', self.thisContext(this.onScroll));
    },
    
    disableInfiniteScroll: function () {
        $(window).off('scroll');
    },
    
    toggleOnlyMineClicked: function (event) {
    	var self = this;
    	self.options.onlyMine = event.target.checked;
    	// save ui pref
    	self.uiPrefsView.saveUiPrefs({'timeline__only_mine': self.options.onlyMine});
    	self.resetAndLoad();
    },
    
    removeEmptyDivs: function () {
    	var self = this;
    	self.$el.find('.remove-if-prev-empty').each(function(){
			var $item = $(this);
			if ($item.prev().text().replace(/\s/g, '').length == 0) {
				$item.remove();
			}
		});
    	self.$el.find('.remove-if-next-empty').each(function(){
			var $item = $(this);
			if ($item.next().text().replace(/\s/g, '').length == 0) {
				$item.remove();
			}
		});
    	self.$el.find('.remove-if-empty').each(function(){
			var $item = $(this);
			if ($item.text().replace(/\s/g, '').length == 0) {
				$item.remove();
			}
		});
    },
    
    /** Handles events for infinite scroll */
    onScroll: function (event) {
    	var self = this;
    	// only check scrolling if the timeline is visible
    	if (self.$el.is(':visible')) {
    		var $window = $(window);
    		if ($window.height() + $window.scrollTop() >= $(document).height() - 250) {
    			self.load();  // load() handles state checks itself so it's safe to call multiple times.
    		}
    	}
    },

});
