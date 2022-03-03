'use strict';

var DelegatedWidgetView = require('views/base/delegated-widget-view');
var util = require('lib/util');

module.exports = DelegatedWidgetView.extend({

	app: null,
    template: require('navbar/notification-widget'),
    
    fetchURL: '/profile/api/alerts/get/', // overridden for subview
    
    // the notification-show button in the navbar
    $notificationButtonEl: null,
    
    // the messages-show button in the navbar
    $messagesButtonEl: null,
    
    // the setTimeout object
	pollIntervalObj: null,
	
    // will be set to self.options during initialization
    defaults: {
    	
    	type: null, // the type of the content the widget displays
    	loadMoreEnabled: true, // widget template options
    	
    	pollInterval: 60000, // polling interval in ms
    	
    	// for resumed connections, after how minutes of *not having polled*,
    	// will the entire widget be reloaded instead of polling new data 
    	pollResetMinutes: 60, // reset interval in minutes
        
        state: {
            newestTimestamp: null,
            unseenCount: 0,
            hasUnrenderedItems: true,
            lastPollDate: null,
            originalPageTitle: null,
        }
    },
    
    // The DOM events specific to an item.
    events: {
    	'click .show-more': 'onShowMoreClicked',
    },
    
    initialize: function (options, app) {
        var self = this;
        self.app = app;
        DelegatedWidgetView.prototype.initialize.call(self, options);
        self.options.type = options.type; // would have happened in initialize already but let's be explicit
        
        self.$notificationButtonEl = $('#navbar-notifications-button');
        self.$messagesButtonEl = $('#navbar-messages-button');
        
        // events that have to be defined here because they happen in the notification button:
        self.$notificationButtonEl.on('click', self.thisContext(self.onNotificationButtonClicked));
        
        self.state.originalPageTitle = document.title;
    },
    
    /** Overriding base function for unique widget ID. */
    getWidgetId: function() {
        return 'notification-widget';
    },
    
    /** Overriding params for request */
    getParamsForFetchRequest: function(loadOptions) {
    	var self = this;
    	if (typeof loadOptions !== "undefined" && loadOptions.isPoll == true) {
            return {
                urlSuffix: self.state.newestTimestamp,
                urlParams: null
            };
    	}
    	var urlParams = null;
        if (self.options.loadMoreEnabled && self.state.offsetTimestamp) {
            urlParams = {
                'offset_timestamp': self.state.offsetTimestamp,
            }
        }
        return {
            urlSuffix: null,
            urlParams: urlParams,
        }
    },
    
    /** Handles data that has been loaded.
        We are *not* calling super() here! */
    handleData: function (response) {
        var self = this;
        var data = response['data'];
        
        if (data.polled_timestamp) {
            // was a poll query. prepend new items before existing items
            if (data['items'].length > 0) {
                self.addNewerItems(data['items']);
                self.state.hasUnrenderedItems = true;                
            }
        } else if (self.state.offsetTimestamp) {
            // was a load-more query. append new items to existing items
            Array.prototype.push.apply(self.widgetData['items'], data['items']);
            // always set true, so we re-render always (make the load-more button disappear on 0 new items) 
            self.state.hasUnrenderedItems = true; 
        } else {
            // first data load query, set data and init polling
            self.widgetData = data;
            self.state.hasUnrenderedItems = true;
            self.initPoll();
        }
        
        if (!data.polled_timestamp && self.options.loadMoreEnabled) {
            if ('has_more' in data) {
                self.state.hasMore = data['has_more'];
            }
            if ('offset_timestamp' in data && data['offset_timestamp']) {
                self.state.offsetTimestamp = data['offset_timestamp'];
            }
        }
        
        // if given, set the timestamp of the newest item, from which on we will poll
        if (data['newest_timestamp'] !== "undefined" && data['newest_timestamp']) {
            self.state.newestTimestamp = data['newest_timestamp'];
        }
        var counterNumbers = false;
        if (data['unseen_count'] !== "undefined" && data['unseen_count'] >= 0) {
            self.state.unseenCount = data['unseen_count'];
            counterNumbers = true;
        }
        if (data['unread_messages_count'] !== "undefined" && data['unread_messages_count'] >= 0) {
            self.state.unreadMessagesCount = data['unread_messages_count'];
            counterNumbers = true;
        }
        if (counterNumbers == true) {
            self.afterRender();
            self.updatePageTitle();
        }
    },
    
    /** Prepends the given items to the existing items, eg. after a poll event.
        This will remove any existing items with the same id as any of the new items
        (in this case they were refreshed on the server) */
    addNewerItems: function (items) {
        var self = this;
        var oldItems = self.widgetData['items'];
        // remove same-id old items
        for (var i=oldItems.length-1; i >= 0; i--) {
            var oldItemId = oldItems[i].id;
            var contained = false;
            for (var j=0; j < items.length; j++) {
                if (items[j].id == oldItemId) {
                    contained = true;
                    break;
                }
            }
            if (contained) {
                oldItems.splice(i, 1);
            }            
        }
        Array.prototype.push.apply(items, oldItems)
        self.widgetData['items'] = items;
    },
    
    /** Initialize polling */
    initPoll: function () {
        var self = this;
        if (self.pollIntervalObj == null) {
            self.pollIntervalObj = setTimeout(self.thisContext(self.pollFunction), self.options.pollInterval);
        }
    },
    
    /** Target interval function for each poll */
    pollFunction: function () {
        var self = this;
        var reload = false;
        // find out if this window has been a long time since last poll,
        // and if so, reload the widget instead of polling
        if (self.state.lastPollDate !== null) {
            var diff = Math.abs(self.state.lastPollDate - new Date());
            var minutes = Math.floor((diff/1000)/60);
            reload = minutes >= self.options.pollResetMinutes;
        }
        if (reload) {
            self.reloadWidget();  
        } else {
            // retrieve new items. if any, self.handleData() will handle the poll differently
            self.load({
                'isPoll': true
            });
            self.state.lastPollDate = new Date();
            // renew poll
            self.pollIntervalObj = setTimeout(self.thisContext(self.pollFunction), self.options.pollInterval);
        }
    },
    
    /** Stops polling */
    stopPoll: function () {
        var self = this;
        clearTimeout(self.pollIntervalObj);
        self.pollIntervalObj = null;
    },
    
    /** Reloads the entire widget anew, with fresh data */
    reloadWidget: function () {
        var self = this;
        self.stopPoll();
        self.state.offsetTimestamp = null;  
        self.state.newestTimestamp = null;
        self.state.unseenCount = 0;
        self.state.unreadMessagesCount = 0;
        self.state.lastPollDate = null;
        self.load();
    },
    
    render: function () {
        var self = this;
        
        // only render items if we have unrendered items (ie. not on a poll with 0 new items)
        if (self.state.hasUnrenderedItems) {
            self.state.hasUnrenderedItems = false;
            DelegatedWidgetView.prototype.render.call(self);
            util.log('# ## Rendered notification widget ' + self.widgetId);
        }
        // piggybacking on this poll, we refresh the moment dates on the entire page!
        $.cosinnus.renderMomentDataDate();
        return self;
    },
    
    afterRender: function () {
        var self = this;
        // update out-of-frame elements
        if (self.state.unseenCount && self.state.unseenCount > 0) {
            self.$notificationButtonEl.find('.message-counter').text(self.state.unseenCount).show();
        } else {
            self.$notificationButtonEl.find('.message-counter').hide();
        }
        if (self.state.unreadMessagesCount && self.state.unreadMessagesCount > 0) {
            self.$messagesButtonEl.find('.message-counter').text(self.state.unreadMessagesCount).show();
        } else {
            self.$messagesButtonEl.find('.message-counter').hide();
        }
    },
    
    /** Extend the template data by the controlView's options and state */
    getTemplateData: function () {
        var self = this;
        var data = DelegatedWidgetView.prototype.getTemplateData.call(self);
        return data;
    },
    
    /** Fired when the navbar notification button is clicked */
    onNotificationButtonClicked: function (event) {
        var self = this;
        if (this.$notificationButtonEl.hasClass('collapsed')) {
            // fired only when the menu is opened
            if (self.state.newestTimestamp) {
                self.markSeen();
            }
        } 
    },
    
    /** Posts to the server, sets all alerts older than the newest displayed as seen on the server */
    markSeen: function() {
        var self = this;
        var url = '/profile/api/alerts/markseen/' + self.state.newestTimestamp + '/';
        $.ajax(url, {
            type: 'POST',
            timeout: 15000,
            success: function (response, textStatus, xhr) {
                self.markSeenLocal();
                util.log('Successfully marked as seen!');
            },
            error: function (xhr, textStatus) {
                // marking seen even if it wasn't persisted (even more annoying if not)
                self.markSeenLocal(); 
                util.log('Error during marking as seen!');
            }
        });
    },

    /** Removes the notification button unseen number badge, in local frontend only. */    
    markSeenLocal: function() {
        var self = this;  
        self.state.unseenCount = 0;
        self.afterRender();
        self.updatePageTitle();
    },
    
    /** Updates the page title by prefixing a (3) unread counter to it */
    updatePageTitle: function() {
        var self = this;
        var unseenPrefix = '';
        var totalCount = self.state.unseenCount + self.state.unreadMessagesCount;
        
        if (totalCount > 0) {
            unseenPrefix = '(' + totalCount + ') ';
        }
        document.title = unseenPrefix + self.state.originalPageTitle;  
    },

});
