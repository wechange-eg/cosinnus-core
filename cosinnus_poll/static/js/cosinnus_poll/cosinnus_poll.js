$(function() {
    /** Poll vote page logic  */
    
    $('.poll-option.poll-option-yes:not([data-toggle]), ' +
      '.poll-option.poll-option-maybe:not([data-toggle]), ' +
      '.poll-option.poll-option-no:not([data-toggle])').click(function(event) {
        var $this = $(this);
        if ($(event.target).attr('data-toggle') || $(event.target).parent().attr('data-toggle')) {
            return true;
        }
        
        event.preventDefault();
        var vote_id = $this.attr('data-poll-option-vote-id');
        if (vote_id) {
            // on click of active vote option: cycle through vote choices
            var can_vote_maybe = $this.attr('data-poll-can-vote-maybe') == '1';
            var multiple_votes = $this.attr('data-poll-multiple-votes') == '1';
            
            function setOptionToChoice($item, choice) {
                /** sets an option's css class to the desired 'poll-option-<choice>' and sets the form value for that item */ 
                // remove any choice class
                $item.removeClass('poll-option-yes').removeClass('poll-option-maybe').removeClass('poll-option-no');
                // add selected choice class
                $item.addClass('poll-option-' + choice);
                // set form-input to choice
                var $form_input = $('#' + $item.attr('data-poll-option-vote-id'));
                $form_input.val(choice == 'yes' ? 2 : (choice == 'maybe' ? 1 : 0));
            }
            
            if (multiple_votes) {
                // case 1: multiple votes. cycle this option to the next.
                var current_choice = $this.hasClass('poll-option-yes') ? 'yes' : ($this.hasClass('poll-option-maybe') ? 'maybe' : 'no');
                // cycle to next choice
                var choice_cycle = can_vote_maybe ? ['no', 'yes', 'maybe'] : ['no', 'yes'];
                var cycle_index = choice_cycle.indexOf(current_choice) + 1;
                cycle_index = cycle_index < choice_cycle.length ? cycle_index : 0;
                var next_choice = choice_cycle[cycle_index];
                
                setOptionToChoice($this, next_choice);
            } else {
                // case 2: single votes. set all other options to 'No' and this to 'Yes'. There is no 'maybe' and no 'not chosen'.
                $('.poll-option').each(function(idx, elem) {
                    setOptionToChoice($(elem), 'no');
                });
                setOptionToChoice($this, 'yes');
            }
        };
        
    });
});
