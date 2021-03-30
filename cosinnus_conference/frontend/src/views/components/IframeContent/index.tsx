import React, {useCallback, useEffect, useState} from "react"
import {faArrowsAlt, faCompressArrowsAlt, faExternalLinkAlt} from "@fortawesome/free-solid-svg-icons"
import Iframe from "react-iframe"
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Link
} from "@material-ui/core"
import {FontAwesomeIcon} from "@fortawesome/react-fontawesome"
import clsx from "clsx"
import {FormattedMessage} from "react-intl"

import {useStyles} from "./style"

interface IframeProps {
  url?: string
  html?: string
}

export function IframeContent(props: IframeProps) {
  const { url, html } = props
  const [ fullscreen, setFullscreen ] = useState(false)
  const [leaveOpen, setLeaveOpen] = useState(false)
  const [leaveUrl, setLeaveUrl] = useState("")
  const classes = useStyles()

  // Minimize on ESC key
  const escFunction = useCallback((event) => {
    if(event.keyCode === 27) setFullscreen(false)
  }, [])
  useEffect(() => {
    document.addEventListener("keydown", escFunction, false)
    return () => document.removeEventListener("keydown", escFunction, false)
  }, []);

  // Hack to open confirm dialog for all links within DOM
  function confirmLeave(e: any) {
    // Don't prompt if link is opened in a new tab
    if (e.ctrlKey || e.shiftKey || e.metaKey || (e.button && e.button == 1)) return;
    // Don't prompt if not a detail view
    const detailView = document.getElementsByClassName('detail-view');
    if (detailView.length == 0) return;
    // Don't prompt if link within detail view container (e.g. maximize button)
    if (detailView[0].contains(e.target)) return;
    e.preventDefault()
    var href_target = e.currentTarget.getAttribute("href");
    // Don't prompt on
    if (!href_target || href_target === "#") return;
    setLeaveUrl(href_target)
    setLeaveOpen(true)
    return false
  }
  const links = document.getElementsByTagName('a');
  for (let i = 0; i < links.length; i++) {
    links[i].onclick = confirmLeave;
  }

  return (
    <div className={clsx({
      [classes.iframe]: true,
      [classes.fullscreen]: fullscreen,
      "iframe": true,
    })}>
      <div className={classes.buttons}>
        <Link
          className={classes.newTabLink}
          href={url}
          target="_blank"
        >
          <FontAwesomeIcon icon={faExternalLinkAlt} />
        </Link>
        <Link
          className={classes.fullScreenLink}
          href="#"
          onClick={() => setFullscreen(!fullscreen)}
        >
          <FontAwesomeIcon icon={fullscreen && faCompressArrowsAlt || faArrowsAlt} />
        </Link>
      </div>
      {html && (
        <div dangerouslySetInnerHTML={{__html: html}} />
      ) || (
        <Iframe
          url={url}
          width="100%"
          height="100%"
          allow="display-capture; geolocation; microphone *; camera *; fullscreen *;"
        />
      )}
      <Dialog
        open={leaveOpen}
        onClose={() => setLeaveOpen(false)}
        aria-labelledby="leave-dialog-title"
        aria-describedby="leave-dialog-description"
      >
        <DialogTitle id="leave-dialog-title"><FormattedMessage id="Are you sure you want to leave this video conference?" /></DialogTitle>
        <DialogContent>
          <DialogContentText
            id="alert-dialog-description"
            classes={{
              root: classes.dialogText,
            }}>
            <FormattedMessage id="If you click, you will leave the video conference. Are you sure you want to leave? Tip: Alternatively, you can open the link in a new tab or window and stay in the event." />
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => window.location.href = leaveUrl}>
            <FormattedMessage id="Yes" />
          </Button>
          <Button onClick={() => setLeaveOpen(false)} autoFocus>
            <FormattedMessage id="No" />
          </Button>
        </DialogActions>
      </Dialog>
    </div>
  )
}
