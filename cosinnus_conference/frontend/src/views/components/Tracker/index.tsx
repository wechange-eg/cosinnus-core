import React, {useEffect} from 'react';

export function Tracker(props: {id: number}) {
    useEffect(() => {

        // Track conference event attendance by calling the respective API every minute.
        const intervalId = setInterval(() => {
            fetch(`/api/v2/conferences/${window.conferenceId}/attend_event/?event_id=${props.id}`)
        },
            1000 * 60 * window.conferenceTrackingInterval
        )

        return () => {
            clearInterval(intervalId)
        }
    })
    return (
        <div></div>
    )
}
