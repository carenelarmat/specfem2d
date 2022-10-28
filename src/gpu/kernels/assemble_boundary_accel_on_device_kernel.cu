/*
!========================================================================
!
!                   S P E C F E M 2 D  Version 7 . 0
!                   --------------------------------
!
!     Main historical authors: Dimitri Komatitsch and Jeroen Tromp
!                        Princeton University, USA
!                and CNRS / University of Marseille, France
!                 (there are currently many more authors!)
! (c) Princeton University and CNRS / University of Marseille, April 2014
!
! This software is a computer program whose purpose is to solve
! the two-dimensional viscoelastic anisotropic or poroelastic wave equation
! using a spectral-element method (SEM).
!
! This program is free software; you can redistribute it and/or modify
! it under the terms of the GNU General Public License as published by
! the Free Software Foundation; either version 3 of the License, or
! (at your option) any later version.
!
! This program is distributed in the hope that it will be useful,
! but WITHOUT ANY WARRANTY; without even the implied warranty of
! MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
! GNU General Public License for more details.
!
! You should have received a copy of the GNU General Public License along
! with this program; if not, write to the Free Software Foundation, Inc.,
! 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
!
! The full text of the license is available in file "LICENSE".
!
!========================================================================
*/


__global__ void assemble_boundary_accel_on_device(realw* d_accel, realw* d_send_accel_buffer,
                                                  const int ninterface_el,
                                                  const int max_nibool_interfaces_ext_mesh,
                                                  const int* d_nibool_interfaces_ext_mesh,
                                                  const int* d_ibool_interfaces_ext_mesh,
                                                  const int* inum_inter_elastic) {

  //int bx = blockIdx.y*gridDim.x+blockIdx.x;
  //int tx = threadIdx.x;
  int id = threadIdx.x + blockIdx.x*blockDim.x + blockIdx.y*gridDim.x*blockDim.x;

  int ientry,iglob,num_int;

  for( int iinterface=0; iinterface < ninterface_el; iinterface++) {

     num_int=inum_inter_elastic[iinterface]-1;

     if (id < d_nibool_interfaces_ext_mesh[num_int]) {

      // entry in interface array
      ientry = id + max_nibool_interfaces_ext_mesh*num_int;
      // global index in wavefield
      iglob = d_ibool_interfaces_ext_mesh[ientry] - 1;

      // for testing atomic operations against not atomic operations (0.1ms vs. 0.04 ms)
      // d_accel[3*(iglob)] += d_send_accel_buffer[3*(ientry)];
      // d_accel[3*(iglob)+1] += d_send_accel_buffer[3*(ientry)+1];
      // d_accel[3*(iglob)+2] += d_send_accel_buffer[3*(ientry)+2];

      atomicAdd(&d_accel[2*iglob],d_send_accel_buffer[2*ientry]);
      atomicAdd(&d_accel[2*iglob + 1],d_send_accel_buffer[2*ientry + 1]);
    }
  }
  // ! This step is done via previous function transfer_and_assemble...
  // ! do iinterface = 1, num_interfaces_ext_mesh
  // !   do ipoin = 1, nibool_interfaces_ext_mesh(iinterface)
  // !     array_val(:,ibool_interfaces_ext_mesh(ipoin,iinterface)) = &
  // !          array_val(:,ibool_interfaces_ext_mesh(ipoin,iinterface)) + buffer_recv_vector_gpu(:,ipoin,iinterface)
  // !   enddo
  // ! enddo
}

