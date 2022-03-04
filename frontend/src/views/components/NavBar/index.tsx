import React from 'react'
import AppBar from '@material-ui/core/AppBar'
import Toolbar from '@material-ui/core/Toolbar'
import IconButton from '@material-ui/core/IconButton'
import Typography from '@material-ui/core/Typography'
import InputBase from '@material-ui/core/InputBase'
import Badge from '@material-ui/core/Badge'
import MenuItem from '@material-ui/core/MenuItem'
import Menu from '@material-ui/core/Menu'
import {RootState} from "../../../stores/rootReducer"
import {connect as reduxConnect} from "react-redux"
import {withRouter} from "react-router"
import {useHistory, RouteComponentProps} from "react-router-dom"

import {useStyles} from "./style"
import {FontAwesomeIcon} from "@fortawesome/react-fontawesome"
import {
  faBars,
  faBell,
  faEllipsisV,
  faEnvelope,
  faSearch,
  faUserCircle
} from "@fortawesome/free-solid-svg-icons"
import {FormattedMessage} from "react-intl"
import {fetchSearchResults} from "../../../stores/search/effects";
import {DispatchedReduxThunkActionCreator} from "../../../utils/types";
import {Result} from "../../../stores/search/models";
import {Settings} from "../../../stores/settings/models";

interface NavBarProps {
  authToken: string
  results: Result[]
  settings: Settings
  fetchSearchResults: DispatchedReduxThunkActionCreator<Promise<void>>
}

function mapStateToProps(state: RootState) {
  return {
    authToken: state.auth.token,
    results: state.search.results,
    settings: state.settings
  }
}

const mapDispatchToProps = {
  fetchSearchResults
}


export default function NavBarConnector(props: NavBarProps & RouteComponentProps) {
  const { authToken, results, fetchSearchResults } = props
  const { settings } = props
  const history = useHistory()
  const classes = useStyles()
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null)
  const [mobileMoreAnchorEl, setMobileMoreAnchorEl] = React.useState<null | HTMLElement>(null)
  const isMenuOpen = Boolean(anchorEl)
  const isMobileMenuOpen = Boolean(mobileMoreAnchorEl)

  if (!results) fetchSearchResults("")

  const handleProfileMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget)
  }

  const handleMobileMenuClose = () => {
    setMobileMoreAnchorEl(null)
  }

  const handleMenuClose = () => {
    setAnchorEl(null)
    handleMobileMenuClose()
  }

  const handleMobileMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setMobileMoreAnchorEl(event.currentTarget)
  }

  const menuId = 'primary-search-account-menu'
  const renderMenu = (
    <Menu
      anchorEl={anchorEl}
      anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
      id={menuId}
      keepMounted
      transformOrigin={{ vertical: 'top', horizontal: 'right' }}
      open={isMenuOpen}
      onClose={handleMenuClose}
    >
      <MenuItem onClick={handleMenuClose}>Profile</MenuItem>
      <MenuItem onClick={handleMenuClose}>My account</MenuItem>
    </Menu>
  )

  const mobileMenuId = 'primary-search-account-menu-mobile'
  const renderMobileMenu = (
    <Menu
      anchorEl={mobileMoreAnchorEl}
      anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
      id={mobileMenuId}
      keepMounted
      transformOrigin={{ vertical: 'top', horizontal: 'right' }}
      open={isMobileMenuOpen}
      onClose={handleMobileMenuClose}
    >
      <MenuItem>
        <IconButton aria-label="Show new mails" color="inherit">
          <Badge badgeContent={4} color="secondary">
            <FontAwesomeIcon icon={faEnvelope} />
          </Badge>
        </IconButton>
        <p>Messages</p>
      </MenuItem>
      <MenuItem>
        <IconButton aria-label="Show 11 new notifications" color="inherit">
          <Badge badgeContent={11} color="secondary">
            <FontAwesomeIcon icon={faBell} />
          </Badge>
        </IconButton>
        <p>Notifications</p>
      </MenuItem>
      <MenuItem onClick={handleProfileMenuOpen}>
        <IconButton
          aria-label="Account of current user"
          aria-controls="primary-search-account-menu"
          aria-haspopup="true"
          color="inherit"
        >
          <FontAwesomeIcon icon={faUserCircle} />
        </IconButton>
        <p>
          <FormattedMessage id="Profile" />
        </p>
      </MenuItem>
    </Menu>
  )

  const onSearchKeyPress = (e) => {
    if (e.charCode == 13) {
      fetchSearchResults(e.target.value)
      history.push("/search/")
    }
  }

  return (
    <div className={classes.grow}>
      <AppBar position="fixed">
        <Toolbar>
          <IconButton
            edge="start"
            className={classes.menuButton}
            color="inherit"
            aria-label="open drawer"
          >
            <FontAwesomeIcon icon={faBars} />
          </IconButton>
          {settings && <img className={classes.logo} src={settings.getLogoUrl()} />}
          <div className={classes.search}>
            <div className={classes.searchIcon}>
              <FontAwesomeIcon icon={faSearch} />
            </div>
            <InputBase
              placeholder="Search…"
              classes={{
                root: classes.inputRoot,
                input: classes.inputInput,
              }}
              inputProps={{ 'aria-label': 'search' }}
              onKeyPress={onSearchKeyPress}
            />
          </div>
          <div className={classes.grow} />
          {authToken && (
            <div>
              <div className={classes.sectionDesktop}>
                <IconButton aria-label="show 4 new mails" color="inherit">
                  <Badge badgeContent={4} color="secondary">
                    <FontAwesomeIcon icon={faEnvelope} />
                  </Badge>
                </IconButton>
                <IconButton aria-label="show 17 new notifications" color="inherit">
                  <Badge badgeContent={17} color="secondary">
                    <FontAwesomeIcon icon={faBell} />
                  </Badge>
                </IconButton>
                <IconButton
                  edge="end"
                  aria-label="account of current user"
                  aria-controls={menuId}
                  aria-haspopup="true"
                  onClick={handleProfileMenuOpen}
                  color="inherit"
                >
                  <FontAwesomeIcon icon={faUserCircle} />
                </IconButton>
              </div>
              <div className={classes.sectionMobile}>
                <IconButton
                  aria-label="show more"
                  aria-controls={mobileMenuId}
                  aria-haspopup="true"
                  onClick={handleMobileMenuOpen}
                  color="inherit"
                >
                  <FontAwesomeIcon icon={faEllipsisV} />
                </IconButton>
              </div>
            </div>
          )}
        </Toolbar>
      </AppBar>
      {authToken && renderMobileMenu}
      {authToken && renderMenu}
    </div>
  )
}

export const NavBar = reduxConnect(mapStateToProps, mapDispatchToProps)(
  withRouter(NavBarConnector)
)
