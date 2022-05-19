import {Dispatch} from "redux"

import {ReduxThunkActionCreator} from "../../utils/types"
import {RootState} from "../rootReducer"
import {setAuthToken, setAuthError, setUser, setVersion} from "./actions"
import {fetchTagsByTeam} from "../tags/effects"

/**
 * Fetch authentication token
 *
 * @param {string} email - email
 * @param {string} password - password
 * @param setSubmitting - setSubmitting
 * @param {any} callback - callback
 * @returns {(dispatch: any) => Promise<void>} - return function
 */
export const fetchAuthToken: ReduxThunkActionCreator<[string, string, (isSubmitting: boolean) => void, any],
  Promise<void>> = (email, password, setSubmitting, callback) => dispatch =>
  fetch(`${process.env.API_URL}/token/`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({username: email, password})
  }).then(response => {
    if (response.status === 200) {
      response
        .json()
        .then(data => {
          dispatch(setAuthError(null))
          dispatch(setAuthToken(data.access))
        })
        .then(callback)
    } else {
      dispatch(setAuthError("Invalid username and/or password"))
      setSubmitting(false)
    }
  })
