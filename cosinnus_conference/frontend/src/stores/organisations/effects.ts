import {Dispatch} from "redux"

import {ReduxThunkActionCreator} from "../../utils/types"
import {
  setFetchOrganisationsError,
  setFetchOrganisationsSuccess
} from "./actions"
import {Organisation, OrganisationJson} from "./models"

/**
 * Fetch conference represented organisations
 *
 * @returns {(dispatch: Dispatch) => Promise<void>} - return function
 */
export const fetchOrganisations: ReduxThunkActionCreator<[string],
  Promise<void>> = () => (dispatch: Dispatch) =>
  fetch(`/api/v2/conferences/${window.conferenceId}/organisations/`, {
    method: "GET"
  }).then(response => {
    if (response.status === 200) {
      response.json().then((data: OrganisationJson[]) => {
        dispatch(setFetchOrganisationsSuccess(data.map((json) => Organisation.fromJson(json))))
      })
    } else {
      dispatch(setFetchOrganisationsError("Failed to fetch channels"))
    }
  })
