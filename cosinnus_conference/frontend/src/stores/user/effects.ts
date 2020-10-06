import {Dispatch} from "redux"

import {ReduxThunkActionCreator} from "../../utils/types"
import {RootState} from "../rootReducer"
import {setUser} from "./actions"
import {User} from "./models"

/**
 * Fetch user data
 *
 * @returns {(dispatch: Dispatch, getState: () => RootState) => Promise<void>} - return function
 */
export const fetchUser: ReduxThunkActionCreator<[], Promise<void>> = () => (
  dispatch: Dispatch,
  _getState: () => RootState
) => {
  // const {jwtToken} = getState()
  const headers = new Headers()
  // headers.append("Authorization", "JWT " + authToken)
  headers.append( "Content-Type", "application/json")
  return fetch("/api/v2/current_user/", {
    method: "GET",
    headers: headers
  }).then(response => {
    if (response.status === 200) {
      response.json().then(data => {
        if (data.id) {
          dispatch(setUser(User.fromJson(data)))
        } else {
          window.location.href = "/login/?next=" + window.location.pathname
        }
      })
    }
  })
}
