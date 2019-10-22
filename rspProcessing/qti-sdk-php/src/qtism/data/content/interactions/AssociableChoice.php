<?php
/**
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License
 * as published by the Free Software Foundation; under version 2
 * of the License (non-upgradable).
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
 *
 * Copyright (c) 2013-2015 (original work) Open Assessment Technologies SA (under the project TAO-PRODUCT);
 *
 * @author Jérôme Bogaerts <jerome@taotesting.com>
 * @license GPLv2
 */

namespace qtism\data\content\interactions;

use qtism\common\collections\IdentifierCollection;

/**
 * From IMS QTI:
 *
 * Other interactions involve associating pairs of predefined choices.
 *
 * This is a marker interface.
 *
 * @author Jérôme Bogaerts <jerome@taotesting.com>
 * @see http://en.wikipedia.org/wiki/Marker_interface_pattern
 */
interface AssociableChoice
{
    /**
     * Get the set of choices that this choice may be associated with.
     * 
     * @return \qtism\common\collections\IdentifierCollection
     */
    public function getMatchGroup();
    
    /**
     * Set the set of choices that this choice may be associated with.
     * 
     * @param \qtism\common\collections\IdentifierCollection $matchGroup
     */
    public function setMatchGroup(IdentifierCollection $matchGroup);
}
