import {
  Card,
  CardContent,
  Grid,
  Typography
} from "@material-ui/core"
import React from "react"
import {connect as reduxConnect} from "react-redux"
import {RouteComponentProps} from "react-router-dom"
import {withRouter} from "react-router"
import {FormattedMessage} from "react-intl";
import Iframe from "react-iframe"

import {RootState} from "../../stores/rootReducer"
import {DispatchedReduxThunkActionCreator} from "../../utils/types"
import {useStyles as iframeUseStyles} from "../components/Iframe/style"
import {Content} from "../components/Content/style"
import {Sidebar} from "../components/Sidebar"
import {Channel} from "../../stores/channels/reducer"
import {fetchChannels} from "../../stores/channels/effects"
import {useStyles} from "./style"

interface NetworkingProps {
  channels: Channel[]

  fetchChannels: DispatchedReduxThunkActionCreator<Promise<void>>
}

function mapStateToProps(state: RootState) {
  return {
    channels: state.channels,
  }
}

const mapDispatchToProps = {
  fetchChannels
}

function NetworkingConnector (props: NetworkingProps & RouteComponentProps) {
  const { channels, fetchChannels } = props
  if (!channels) {
    fetchChannels()
  }
  const classes = useStyles()
  const iFrameClasses = iframeUseStyles()
  return (
    <Grid container>
      <Content>
        <Typography component="h1">
          <FormattedMessage
            id="Connect with someone via videochat for 5 minutes"
            defaultMessage="Connect with someone via videochat for 5 minutes"
          />
        </Typography>
        {channels && channels.length > 0 && (
        <Grid container spacing={2}>
          {channels.map((channel, index) => (
          <Grid item key={index} sm={6} className="now">
            <Card className={classes.card}>
              <CardContent>
                <Typography component="span">{channel.name}</Typography>
              </CardContent>
            </Card>
          </Grid>
          ))}
        </Grid>
        )
        || <Typography><FormattedMessage
          id="No networking channels."
          defaultMessage="No networking channels."
        /></Typography>
        }
      </Content>
      <Sidebar elements={(
        <Iframe
          url="https://chat.wechange.de/channel/general"
          width="100%"
          height="100%"
          className={iFrameClasses.iframe}
        />
      )} />
    </Grid>
  )
}

export const Networking = reduxConnect(mapStateToProps, mapDispatchToProps)(
  withRouter(NetworkingConnector)
)
