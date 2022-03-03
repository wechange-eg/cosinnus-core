

$(function() {
    /** Marketplace Offer filter and reload  logic  */
    
    $('.marketplace-option.marketplace-option-yes:not([data-toggle]), ' +
      '.marketplace-option.marketplace-option-maybe:not([data-toggle]), ' +
      '.marketplace-option.marketplace-option-no:not([data-toggle])').click(function(event) {
        var $this = $(this);
        if ($(event.target).attr('data-toggle') || $(event.target).parent().attr('data-toggle')) {
            return true;
        }
        
        event.preventDefault();
        var vote_id = $this.attr('data-marketplace-option-vote-id');
        if (vote_id) {
            // on click of active vote option: cycle through vote choices
            var can_vote_maybe = $this.attr('data-marketplace-can-vote-maybe') == '1';
            var multiple_votes = $this.attr('data-marketplace-multiple-votes') == '1';
            
            function setOptionToChoice($item, choice) {
                /** sets an option's css class to the desired 'marketplace-option-<choice>' and sets the form value for that item */ 
                // remove any choice class
                $item.removeClass('marketplace-option-yes').removeClass('marketplace-option-maybe').removeClass('marketplace-option-no');
                // add selected choice class
                $item.addClass('marketplace-option-' + choice);
                // set form-input to choice
                var $form_input = $('#' + $item.attr('data-marketplace-option-vote-id'));
                $form_input.val(choice == 'yes' ? 2 : (choice == 'maybe' ? 1 : 0));
            }
            
            if (multiple_votes) {
                // case 1: multiple votes. cycle this option to the next.
                var current_choice = $this.hasClass('marketplace-option-yes') ? 'yes' : ($this.hasClass('marketplace-option-maybe') ? 'maybe' : 'no');
                // cycle to next choice
                var choice_cycle = can_vote_maybe ? ['no', 'yes', 'maybe'] : ['no', 'yes'];
                var cycle_index = choice_cycle.indexOf(current_choice) + 1;
                cycle_index = cycle_index < choice_cycle.length ? cycle_index : 0;
                var next_choice = choice_cycle[cycle_index];
                
                setOptionToChoice($this, next_choice);
            } else {
                // case 2: single votes. set all other options to 'No' and this to 'Yes'. There is no 'maybe' and no 'not chosen'.
                $('.marketplace-option').each(function(idx, elem) {
                    setOptionToChoice($(elem), 'no');
                });
                setOptionToChoice($this, 'yes');
            }
        };
        
    });
});
