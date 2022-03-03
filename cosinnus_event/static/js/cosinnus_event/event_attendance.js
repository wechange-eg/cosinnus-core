$(function(){
    $('.event-attendance-button').click(function(){
        var $this = $(this);
        var state_class = $this.attr('data-event-attendance-toggle');
        var attendance_frame = $('.event-attendance');
        if (!attendance_frame.hasClass(state_class) && !attendance_frame.hasClass('attendance-busy')) {
            var original_classes = attendance_frame.attr('class');
            var state_visual_class = '';
            var state_request_param = null;
            if (state_class == 'event-attendance-no-choice') {
                state_request_param = -1;
                state_visual_class = 'app-calendar';
            } else if (state_class == 'event-attendance-going') {
                state_request_param = 2;
                state_visual_class = 'app-calendar';
            } else if (state_class == 'event-attendance-maybe') {
                state_request_param = 1;
                state_visual_class = 'app-todos';
            } else if (state_class == 'event-attendance-not-going') {
                state_request_param = 0;
                state_visual_class = 'app-etherpad';
            }
            attendance_frame
                .removeClass('event-attendance-going')
                .removeClass('event-attendance-maybe')
                .removeClass('event-attendance-not-going')
                .removeClass('event-attendance-no-choice')
                .removeClass('app-calendar')
                .removeClass('app-todos')
                .removeClass('app-etherpad')
                .addClass(state_class)
                .addClass(state_visual_class)
                .addClass('attendance-busy');
            
            // disabling button needs a delay or mouse-down won't close the menu
            $('.attendance-status.attendance-status-success').stop().hide().css('opacity', 0);
            $('.attendance-status.attendance-status-error').stop().hide().css('opacity', 0);
            $('.attendance-status.attendance-status-working').show();
            setTimeout(function() {
                attendance_frame.find('button[data-toggle="dropdown"]')
                    .attr('data-toggle', '_dropdown');
            }, 100);
                
            // todo: trigger ajax POST
            $.post( "assign_attendance/", { target_state: state_request_param }, "json")
            .done(function( data ) {
                $('.attendance-status.attendance-status-success').show().css('opacity', 1).delay(1000).fadeOut(2000);
            })
            .fail(function() {
                $('.attendance-status.attendance-status-error').show().css('opacity', 1).delay(1000).fadeOut(2000);
                attendance_frame.attr('class', original_classes).removeClass('open');
            })
            .always(function() {
                $('.attendance-status.attendance-status-working').hide();
                setTimeout(function() {
                    attendance_frame.removeClass('attendance-busy');
                    attendance_frame.find('button[data-toggle="_dropdown"]')
                            .attr('data-toggle', 'dropdown');
                }, 110);
            });
            
        };
        
    });
});
