import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import axios from "axios";

import authHeader from '../utils/auth-header';
import { RootState } from ".";

export interface UserJson {
    id: number
    username: string
    first_name?: string
    last_name?: string
    is_admin?: boolean
}

export interface UserProps {
    id?: number
    username?: string
    firstName?: string
    lastName?: string
    isAdmin?: boolean
}

export class User {
    props: UserProps

    public constructor(props: UserProps) {
        this.props = props
    }

    /**
     * Convert JSON response data into an object
     *
     * @param json - response data in JSON format
     * @returns {User} - User object
     */
    public static fromJson(json: UserJson): User {
        const props: UserProps = {
            id: json.id,
            username: json.username,
            firstName: json.first_name,
            lastName: json.last_name,
            isAdmin: json.is_admin,
        }

        return new User(props)
    }

    /**
     * Convert an object into JSON
     *
     * @returns {UserJson} - object in JSON format
     */
    toJson(): UserJson {
        const props = this.props
        return {
            id: props.id,
            username: props.username,
            first_name: props.firstName,
            last_name: props.lastName,
            is_admin: props.isAdmin,
        }
    }
}

const API_URL = `${process.env.API_URL}`;

export const fetchUser = createAsyncThunk<UserProps, void, {state: RootState }>(
  "user/fetch",
  async (
    values: null,
    { dispatch, getState }
  ): Promise<UserProps | undefined> => {
    const { accessToken } = getState().auth;
    const { data } = await axios.get<UserJson>(
      `${API_URL}/current_user/`,
      { headers: authHeader(accessToken) }
    );
    return User.fromJson(data).props;
  }
);

const userSlice = createSlice({
  name: "user",
  initialState: {} as UserProps,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchUser.fulfilled, (state, action) => {
        if (!action.payload) return;
        state.user = action.payload
      })
  },
});

export const {} = userSlice.actions;
export default userSlice.reducer;
