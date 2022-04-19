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

import {RootState} from "../../stores/rootReducer"
import {DispatchedReduxThunkActionCreator} from "../../utils/types"
import {Content} from "../components/Content/style"
import {Sidebar} from "../components/Sidebar"
import {Organization as OrganizationModel} from "../../stores/organizations/reducer"
import {fetchOrganizations} from "../../stores/organizations/effects"
import {useStyles} from "./style"
import {ManageRoomButtons} from "../components/ManageRoomButtons"
import {Room} from "../../stores/room/models"

interface OrganizationsProps {
  organizations: OrganizationModel[]
  fetchOrganizations: DispatchedReduxThunkActionCreator<Promise<void>>
  room: Room
}

function mapStateToProps(state: RootState) {
  return {
    organizations: state.organizations,
    room: state.room,
  }
}

const mapDispatchToProps = {
  fetchOrganizations
}

function OrganizationsConnector (props: OrganizationsProps & RouteComponentProps) {
  const { organizations, fetchOrganizations, room } = props
  if (!organizations) {
    fetchOrganizations()
  }
  const classes = useStyles()
  return (
    <Grid container>
      <Content>
        <Typography component="h1">
          <FormattedMessage id="Represented organizations" />
        </Typography>
        {organizations && organizations.length > 0 && (
        <Grid container spacing={2}>
          {organizations.map((organization, index) => (
          <Grid item key={index} sm={6} className="now">
            <Card className={classes.card}>
            <CardMedia
                component="img"
                alt={organization.props.name}
                height="100"
                image={organization.props.imageUrl}
                title={organization.props.name}
              />
              <CardContent>
                <Typography component="span">{organization.props.name}</Typography>
                <Typography component="p">{organization.props.description}</Typography>
                <Typography component="span">{organization.props.topics.join(", ")}</Typography>
                <Typography component="span">{organization.props.location}</Typography>
              </CardContent>
            </Card>
          </Grid>
          ))}
        </Grid>
        )
        || <Typography><FormattedMessage id="No represented organizations."/></Typography>
        }
        <ManageRoomButtons />
      </Content>
      {room.props.showChat && room.props.url && <Sidebar url={room.props.url} />}
    </Grid>
  )
}

export const Organizations = reduxConnect(mapStateToProps, mapDispatchToProps)(
  withRouter(OrganizationsConnector)
)
