import * as React from "react"
import { Redirect, Route, RouteProps } from "react-router-dom"
import {Loading} from "../components/Loading"

export interface ProtectedRouteProps extends RouteProps {
  isAuthenticated: boolean
  authPath?: string
  isAllowed?: boolean
  restrictedPath?: string
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = props => {
  let redirectPath = ""
  if (!props.isAuthenticated) {
    redirectPath = props.authPath
  }
  if (redirectPath) {
    const renderComponent = () => <Redirect to={{ pathname: redirectPath }} />
    return <Route {...props} component={renderComponent} render={undefined} />
  } else {
    return <Route {...props} />
  }
}
