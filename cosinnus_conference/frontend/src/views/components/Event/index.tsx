import React, {useState} from "react"
import {Typography} from "@material-ui/core"
import {FormattedMessage} from "react-intl"

import {Event as EventModel} from "../../../stores/events/models"
import {Main} from "../Main/style"
import {Content} from "../Content/style"
import {IframeContent} from "../IframeContent"
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
} from "@material-ui/core"
import {EventButtons} from "../EventButtons"
import {Loading} from "../Loading"
import {Sidebar} from "../Sidebar"
import {EventRoomState} from "../../../stores/events/reducer"
import {useStyles} from "./style"

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
  const [allow, setAllow] = useState('')
  const [loadFinished, setLoadFinished] = useState(false)
  const [fetching, setFetching] = useState(false)
  const [consentOpen, setConsentOpen] = useState(false)
  const [consentGiven, setConsentGiven] = useState(false)
  const classes = useStyles()
  
  function adjustAllowBasedOnUrl(url) {
    /** Set the allow property of the iframe to the domain of the target URL */
    try {
      var domain = 'https://' + url.split('/')[2];
      var allowStr = "display-capture {0}; geolocation {0}; microphone {0}; camera {0}; fullscreen {0};"
      setAllow(allowStr.format(domain));
    } catch (error) {
      console.error('Error during IFrame allow property adjustment' + error);
    }
  }
  function fetchEventUrl(skipConsentPopup) {
    if (!url) {
      if (!event.props.isQueueUrl) {
        adjustAllowBasedOnUrl(event.props.url);
        setUrl(event.props.url);
      } else if (!url && !fetching) {
        setFetching(true);
        
        fetch(event.props.url, {
          method: "GET"
        }).then(response => {
          setFetching(false);
          if (response.status === 200) {
            response.json().then((data: EventResponse) => {
              if (data.status === 'DONE') {
                if (data.recorded_meeting && !consentGiven && !skipConsentPopup) {
                  // show a popup asking the user for recording consent.
                  // we discard data.url here and re-fetch the join url later if consentGiven==true.
                  // otherwise the join url might be stale if a user takes a long time to answer the popup
                  setConsentOpen(true);
                  return;
                }
                adjustAllowBasedOnUrl(data.url);
                setUrl(data.url);
                
              } else if (data.status === 'ERROR') {
                setUrl('ERROR');
              } else {
                setTimeout(fetchEventUrl, 2000);
              }
            })
          } else {
            setUrl('ERROR');
          }
        }).catch(response => {
          setFetching(false);
          setTimeout(fetchEventUrl, 5000);
        })
      }
    }
  }
  // Not loading events anymore and events URL given (instead of HTML)?
  if (events && !events.loading && events.events && event && event.props.url && !url && !fetching && !consentOpen && !loadFinished) {
    setLoadFinished(true);
    fetchEventUrl();
  }

  return (
    <Main container>
      {(event && (url && url === 'ERROR') && (
        <Content className="fullheight">
          <Typography><FormattedMessage id="Event could not be loaded because of a server error."/></Typography>
        </Content>
      ))
      || (event && (url && url === 'USERDECLINED') && (
        <Content className="fullheight">
          <Typography><FormattedMessage id="You can only join this meeting if you accept being recorded. To join this meeting please reload this page to try again."/></Typography>
        </Content>
      ))
      || (event && (url || event.props.rawHtml) && (
        <Content className="fullheight detail-view">
          <Typography component="h1">{event.props.title}</Typography>
          {event.props.noteHtml && (
            <div className="description" dangerouslySetInnerHTML={{__html: event.props.noteHtml}} />
          )}
          <IframeContent url={url} html={event.props.rawHtml} allow={allow} />
          <EventButtons event={event} />
        </Content>
      ))
      || ((events && events.loading) || (events && !events.loading && events.events && event && event.props.url)) && (
        <Content className="fullheight"><Loading /></Content>
      ) 
      || (
        <Content className="fullheight">
          <Typography><FormattedMessage id="Event not found."/></Typography>
        </Content>
      )}
      
      {event && event.props.showChat && event.props.chatUrl && <Sidebar url={event.props.chatUrl} />}
      
      <Dialog
        open={consentOpen}
        onClose={function(){setUrl('USERDECLINED');setConsentOpen(false)}}
        aria-labelledby="consent-record-dialog-title"
        aria-describedby="consent-record-dialog-description"
      >
        <DialogTitle id="consent-record-dialog-title"><FormattedMessage id="Do you consent to be recorded?" /></DialogTitle>
        <DialogContent>
          <DialogContentText
            id="consent-record-dialog-description"
            classes={{
              root: classes.dialogText,
            }}>
            <FormattedMessage id="This session may be recorded by the organizers. By continuing, you consent to be recorded. This includes audio, video, chat, shared notes and whiteboard activities. The recording may be shared according to the organizers." />
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={function(){setConsentGiven(true);setConsentOpen(false);fetchEventUrl(true)}} autoFocus>
            <FormattedMessage id="Yes" />
          </Button>
          <Button onClick={function(){setUrl('USERDECLINED');setConsentOpen(false)}}>
            <FormattedMessage id="No" />
          </Button>
        </DialogActions>
      </Dialog>
    </Main>
  )
}
