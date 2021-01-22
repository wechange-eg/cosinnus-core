import React, {useState} from "react"
import {Typography} from "@material-ui/core"
import {FormattedMessage} from "react-intl"

import {Event as EventModel} from "../../../stores/events/models"
import {Main} from "../Main/style"
import {Content} from "../Content/style"
import {IframeContent} from "../IframeContent"
import {EventButtons} from "../EventButtons"
import {Loading} from "../Loading"
import {EventRoomState} from "../../../stores/events/reducer"

interface EventResponse {
  status: string
  url?: string
}

interface EventProps {
  events: EventRoomState
  event: EventModel
}

export function Event(props: EventProps) {
  const {events, event} = props
  const [url, setUrl] = useState('')

  function fetchEventUrl() {
    if (!url) {
      fetch(event.props.url, {
        method: "GET"
      }).then(response => {
        if (response.status === 200) {
          response.json().then((data: EventResponse) => {
            if (data.status === 'DONE') {
              setUrl(data.url);
            } else {
              setTimeout(fetchEventUrl, 3000);
            }
          })
        }
      })
    }
  }
  // Not loading events anymore and events URL given (instead of HTML)?
  if (events && !events.loading && events.events && event && event.props.url) {
    fetchEventUrl();
  }

  return (
    <Main container>
      {(event && (url || event.props.rawHtml) && (
        <Content className="fullheight detail-view">
          <Typography component="h1">{event.props.title}</Typography>
          {event.props.noteHtml && (
            <div className="description" dangerouslySetInnerHTML={{__html: event.props.noteHtml}} />
          )}
          <IframeContent url={url} html={event.props.rawHtml} />
          <EventButtons event={event} />
        </Content>
      ))
      || (events && events.loading) && (
        <Content className="fullheight"><Loading /></Content>
      ) || (
        <Content className="fullheight">
          <Typography><FormattedMessage id="Event not found."/></Typography>
        </Content>
      )}
    </Main>
  )
}
