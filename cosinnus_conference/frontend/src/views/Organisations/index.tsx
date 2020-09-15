import {
  Card,
  CardContent, CardMedia,
  Grid, Chip,
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
import {Organisation} from "../../stores/organisations/reducer"
import {fetchOrganisations} from "../../stores/organisations/effects"
import {useStyles} from "./style"

interface OrganisationsProps {
  organisations: Organisation[]

  fetchOrganisations: DispatchedReduxThunkActionCreator<Promise<void>>
}

function mapStateToProps(state: RootState) {
  return {
    organisations: state.organisations,
  }
}

const mapDispatchToProps = {
  fetchOrganisations
}

function OrganisationsConnector (props: OrganisationsProps & RouteComponentProps) {
  const { organisations, fetchOrganisations } = props
  if (!organisations) {
    fetchOrganisations()
  }
  const classes = useStyles()
  const iFrameClasses = iframeUseStyles()
  return (
    <Grid container>
      <Content>
        <Typography component="h1">
          <FormattedMessage id="Represented organisations" defaultMessage="Represented organisations" />
        </Typography>
        {organisations && organisations.length > 0 && (
        <Grid container spacing={2}>
          {organisations.map((organisation, index) => (
          <Grid item key={index} sm={6} className="now">
            <Card className={classes.card}>
            <CardMedia
                component="img"
                alt={organisation.props.name}
                height="100"
                image={organisation.props.imageUrl}
                title={organisation.props.name}
              />
              <CardContent>
                <Typography component="span">{organisation.props.name}</Typography>
                <Typography component="p">{organisation.props.description}</Typography>
                <Typography component="span">{organisation.props.topics.join(", ")}</Typography>
                <Typography component="span">{organisation.props.location}</Typography>
              </CardContent>
            </Card>
          </Grid>
          ))}
        </Grid>
        )
        || <Typography><FormattedMessage
          id="No represented organisations."
          defaultMessage="No represented organisations."
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

export const Organisations = reduxConnect(mapStateToProps, mapDispatchToProps)(
  withRouter(OrganisationsConnector)
)
