import {Dispatch} from "redux"

import {ReduxThunkActionCreator} from "../../utils/types"
import {
  setFetchOrganizationsError,
  setFetchOrganizationsSuccess
} from "./actions"
import {Organization, OrganizationJson} from "./models"

/**
 * Fetch conference represented organizations
 *
 * @returns {(dispatch: Dispatch) => Promise<void>} - return function
 */
export const fetchOrganizations: ReduxThunkActionCreator<[string],
  Promise<void>> = () => (dispatch: Dispatch) =>
  fetch(`/api/v2/conferences/${window.conferenceId}/organizations/`, {
    method: "GET"
  }).then(response => {
    if (response.status === 200) {
      response.json().then((data: OrganizationJson[]) => {
        dispatch(setFetchOrganizationsSuccess(data.map((json) => Organization.fromJson(json))))
      })
    } else {
      dispatch(setFetchOrganizationsError("Failed to fetch channels"))
    }
  })
