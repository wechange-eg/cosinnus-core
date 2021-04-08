import React, {useCallback, useEffect, useState} from "react"
import {faArrowsAlt, faCompressArrowsAlt, faExternalLinkAlt} from "@fortawesome/free-solid-svg-icons"
import Iframe from "react-iframe"
import {Link} from "@material-ui/core"
import {FontAwesomeIcon} from "@fortawesome/react-fontawesome"
import clsx from "clsx"

import {useStyles} from "./style"

interface IframeProps {
  url?: string
  html?: string
}

export function IframeContent(props: IframeProps) {
  const { url, html } = props
  const [ fullscreen, setFullscreen ] = useState(false)
  const classes = useStyles()

  // Minimize on ESC key
  const escFunction = useCallback((event) => {
    if(event.keyCode === 27) setFullscreen(false)
  }, [])
  useEffect(() => {
    document.addEventListener("keydown", escFunction, false)
    return () => document.removeEventListener("keydown", escFunction, false)
  }, []);

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
    </div>
  )
}
