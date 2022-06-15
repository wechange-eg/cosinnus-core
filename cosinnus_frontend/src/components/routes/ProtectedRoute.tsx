import React, { FC } from 'react'
import { Redirect, Route, RouteProps } from 'react-router-dom'

// todo: set default values for optional props
export interface ProtectedRouteProps extends RouteProps {
  isAuthenticated: boolean
  authPath?: string
  isAllowed?: boolean
  restrictedPath?: string
}

const ProtectedRoute: FC<ProtectedRouteProps> = (props) => {
  const { isAuthenticated, authPath } = props

  let redirectPath = ''
  if (!isAuthenticated) {
    redirectPath = authPath
  }

  // todo: fix spread operator. not all props should pass through
  if (redirectPath) {
    const renderComponent = () => <Redirect to={{ pathname: redirectPath }} />
    return <Route {...props} component={renderComponent} render={undefined} />
  }
  return <Route {...props} />
}


export default ProtectedRoute
