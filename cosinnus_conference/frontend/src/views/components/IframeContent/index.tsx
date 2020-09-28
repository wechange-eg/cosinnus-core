import React, {useCallback, useEffect, useState} from "react"
import Iframe from "react-iframe"

import {useStyles} from "./style"
import {Link} from "@material-ui/core"
import {FontAwesomeIcon} from "@fortawesome/react-fontawesome"
import {faArrowsAlt, faCompressArrowsAlt, faExternalLinkAlt, faLink} from "@fortawesome/free-solid-svg-icons"
import clsx from "clsx"

interface IframeProps {
  url: string
}

export function IframeContent(props: IframeProps) {
  const { url } = props
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
      <Iframe
        url={url}
        width="100%"
        height="100%"
        allow="display-capture; geolocation; microphone *; camera *"
      />
    </div>
  )
}
