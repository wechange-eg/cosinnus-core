import React, {useEffect} from 'react';

export function Tracker(props: {id: number}) {
    useEffect(() => {

        const intervalId = setInterval(() => {

            if (window["_paq"]) {
                try {
                    // Use Matomo's TrackEvent feature to track conference and conference-event attendance.
                    // The event data represents the attendance time, as the value "1" is pushed every minute.
                    window["_paq"].push(['trackEvent', 'ConferenceEvent', 'attendance', `conference_${window.conferenceId}`, 1])
                    window["_paq"].push(['trackEvent', 'ConferenceEvent', 'attendance', `conference-event_${props.id}`, 1])
                } catch (e) {
                    console.warn('Matomo trackEvent Error')
                }
            }
        },
            1000 * 60
        )

        return () => {
            clearInterval(intervalId)
        }
    })
    return (
        <div></div>
    )
}
